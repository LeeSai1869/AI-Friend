"""WebSocket server that exposes CentralMind to the app.

Run with:
    python3 main.py --serve

The server listens on 127.0.0.1:8765.

Accepted JSON messages:
    { "op": "inventory" }                          -> ask for the domain list
    { "op": "list_chats" }                         -> ask for all chats
    { "text": "...", "intent": "ask|...", ... }    -> a chat message

Sent JSON messages:
    { "op": "inventory_result", "domains": [...] }
    { "op": "chats_result", "chats": [...] }
    { "role": "mind", "text": "..." }
    { "role": "system", "text": "..." }
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from auth_service import AuthService, AuthenticationError
from guard.contract import GuardPrincipal
from guard.layer import GuardLayer
from guard.production_policy import (
    build_production_effect_policy,
    build_production_guard_policy,
)
from section_4_chatbox import Chatbox
from mind import CentralMind


from section_4_chatbox import ChatRuntime
HOST = "127.0.0.1"
PORT = 8765


def _process_exists(pid: int) -> bool:
    """Return whether the Section 0 owner process still exists."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


async def _watch_app_owner(
    app_owner_pid: int,
    app_runtime_token: str,
) -> None:
    """Fail-safe: terminate this runtime if its owning Section 0 app dies.

    Normal shutdown remains owned by Section 0. This watcher exists only so
    an abnormal GUI death cannot leave an app-owned backend running forever.

    The runtime token is intentionally required with the PID so app-owned
    launches are explicitly distinguished from standalone development runs.
    """
    if not app_runtime_token:
        raise RuntimeError("app runtime token is required for owned runtime")

    while True:
        await asyncio.sleep(0.5)

        if not _process_exists(app_owner_pid):
            print(
                "[server] Section 0 owner disappeared "
                f"(pid={app_owner_pid}, runtime={app_runtime_token}); "
                "shutting down owned runtime"
            )
            return


def _default_auth_database() -> Path:
    """Return the private per-user authentication database location.

    Authentication material intentionally lives outside the project tree so
    project file-reading tools cannot expose credential or session storage.
    """
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "AI Friend V1"
        / "auth"
        / "auth.sqlite3"
    )


def _is_within_root(root: Path, target: Path) -> bool:
    """Return whether a resolved target is inside or equal to root."""
    root = Path(root).resolve()
    target = Path(target).resolve()
    return target == root or root in target.parents


class AppChatbox(Chatbox):
    """A chatbox that streams to a WebSocket instead of stdin/stdout."""

    def __init__(self, websocket):
        super().__init__()
        self.websocket = websocket
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None

    def ask(self, question):
        # The current turn ends with structured questions. A later UI turn
        # supplies the answer through Chat's durable context; never guess.
        return None

    def _emit(self, message):
        if self.loop is None or self.loop.is_closed():
            return
        def schedule():
            task = self.loop.create_task(self.websocket.send(json.dumps(message)))
            task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        self.loop.call_soon_threadsafe(schedule)

    def notify(self, message):
        self._emit({"role": "system", "text": str(message)})

    def present(self, response):
        self._emit({"role": "mind", "text": str(response.get("output", response)) if isinstance(response, dict) else str(response)})

    def tool_status(self, message):
        self._emit({"role": "tool", "text": message})


class SessionRuntimes:
    """One serialized Mind per backend-validated application session.

    Windows sharing the Tauri session share component context. Different
    authenticated sessions never share principals or mutable domain state.
    """
    def __init__(self, auth_service):
        self.auth_service = auth_service
        self._runtimes = {}
        self._subscribers = {}

    def resolve(self, token, factory):
        for known in list(self._runtimes):
            try:
                self.auth_service.validate_session(known)
            except AuthenticationError:
                self._runtimes.pop(known, None)
        if token not in self._runtimes:
            self._runtimes[token] = (factory(), asyncio.Lock())
        return self._runtimes[token]

    def subscribe(self, token, websocket):
        self._subscribers.setdefault(token, set()).add(websocket)

    def unsubscribe(self, websocket):
        for subscribers in self._subscribers.values():
            subscribers.discard(websocket)

    async def publish(self, token, message):
        for websocket in list(self._subscribers.get(token, ())):
            try:
                await websocket.send(json.dumps(message))
            except Exception:
                self._subscribers[token].discard(websocket)

    def forget(self, token):
        self._runtimes.pop(token, None)
        self._subscribers.pop(token, None)


def _guard_principal_from_account(account: dict) -> GuardPrincipal:
    """Convert trusted AuthService output into Guard identity.

    Only backend-authenticated account data belongs here. Client JSON
    must never be converted directly into an authenticated principal.
    """
    if not isinstance(account, dict):
        raise AuthenticationError(
            "trusted authenticated account required"
        )

    username = account.get("username")
    role = account.get("role")

    if not isinstance(username, str) or not username.strip():
        raise AuthenticationError(
            "authenticated account has no valid username"
        )

    if not isinstance(role, str) or not role.strip():
        raise AuthenticationError(
            "authenticated account has no valid role"
        )

    return GuardPrincipal(
        principal_id=username.strip(),
        kind="human",
        role=role.strip().lower(),
        authenticated=True,
        source="auth_service",
    )


async def handle_client(
    websocket,
    project_root: Path,
    auth_service: AuthService | None = None,
    runtimes: SessionRuntimes | None = None,
):
    print("[server] client connected")

    # Authentication is fail-closed.  A caller that forgets to provide the
    # shared AuthService does not receive an unauthenticated Central Mind.
    session_token = None
    account = None
    chatbox = None
    mind = None
    operation_lock = asyncio.Lock()

    def resolve_mind(token, **kwargs):
        if runtimes is None:
            return CentralMind(**kwargs), asyncio.Lock()
        return runtimes.resolve(token, lambda: CentralMind(**kwargs))

    try:
        async for raw in websocket:
            try:
                data = json.loads(raw)
            except Exception:
                continue

            if not isinstance(data, dict):
                continue
            op = data.get("op")

            # ---- authentication status ------------------------------------
            if op == "auth_status":
                authenticated = False
                status_account = None

                # A connection-local token is not authority by itself.
                # Revalidate it through AuthService so auth_status observes
                # expiry, logout, and the one-active-session revocation rule.
                if auth_service is not None and session_token:
                    try:
                        status_account = auth_service.validate_session(
                            session_token
                        )
                        authenticated = True
                    except AuthenticationError:
                        # The connection held stale authority. Clear all
                        # application state exactly as the protected-request
                        # authentication boundary does.
                        session_token = None
                        account = None
                        chatbox = None
                        mind = None

                await websocket.send(json.dumps({
                    "op": "auth_status_result",
                    "authenticated": authenticated,
                    "account": status_account,
                    "registration_enabled": (
                        auth_service.registration_enabled()
                        if auth_service is not None
                        else False
                    ),
                    "auth_available": auth_service is not None,
                }))
                continue

            # ---- public registration --------------------------------------
            if op == "register":
                if auth_service is None:
                    await websocket.send(json.dumps({
                        "op": "register_result",
                        "ok": False,
                        "error": "authentication service unavailable",
                    }))
                    continue

                try:
                    created = auth_service.register(
                        data.get("username"),
                        data.get("password"),
                    )
                except (AuthenticationError, ValueError) as exc:
                    await websocket.send(json.dumps({
                        "op": "register_result",
                        "ok": False,
                        "error": str(exc),
                    }))
                    continue

                await websocket.send(json.dumps({
                    "op": "register_result",
                    "ok": True,
                    "account": created,
                }))
                continue

            # ---- login -----------------------------------------------------
            if op == "login":
                if auth_service is None:
                    await websocket.send(json.dumps({
                        "op": "login_result",
                        "ok": False,
                        "error": "authentication service unavailable",
                    }))
                    continue

                try:
                    login_result = auth_service.login(
                        data.get("username"),
                        data.get("password"),
                    )

                    # Validate the newly issued token through the same path
                    # used by every protected request.
                    candidate_token = login_result["token"]
                    candidate_account = auth_service.validate_session(
                        candidate_token
                    )

                    # Central Mind is created only after trusted backend
                    # authentication succeeds. Guard identity is derived
                    # only from the validated backend account.
                    candidate_principal = (
                        _guard_principal_from_account(
                            candidate_account
                        )
                    )

                    candidate_guard = GuardLayer(
                        project_root,
                        policy=build_production_guard_policy(),
                        effect_policy=build_production_effect_policy(),
                    )

                    candidate_chatbox = AppChatbox(websocket)
                    candidate_mind, candidate_lock = resolve_mind(
                        candidate_token,
                        project_root=project_root,
                        chatbox=candidate_chatbox,
                        guards=candidate_guard,
                        principal=candidate_principal,
                    )
                except (AuthenticationError, ValueError) as exc:
                    await websocket.send(json.dumps({
                        "op": "login_result",
                        "ok": False,
                        "error": str(exc),
                    }))
                    continue
                except Exception as exc:
                    # Do not establish an authenticated application session
                    # when Central Mind itself cannot be initialized.
                    try:
                        auth_service.logout(login_result["token"])
                    except Exception:
                        pass
                    await websocket.send(json.dumps({
                        "op": "login_result",
                        "ok": False,
                        "error": f"Central Mind initialization failed: {exc}",
                    }))
                    continue

                session_token = candidate_token
                account = candidate_account
                chatbox = candidate_chatbox
                mind = candidate_mind
                operation_lock = candidate_lock
                if runtimes is not None:
                    runtimes.subscribe(session_token, websocket)

                await websocket.send(json.dumps({
                    "op": "login_result",
                    "ok": True,
                    "token": session_token,
                    "expires_at": login_result["expires_at"],
                    "account": account,
                }))
                await websocket.send(json.dumps({
                    "role": "mind",
                    "text": "Central Mind ready.",
                }))
                continue

            # ---- attach existing application session -----------------------
            #
            # A newly opened Tauri window has a new WebSocket connection.
            # It may present the opaque application-session credential held
            # by the Tauri process, but client JSON is never authority.
            #
            # AuthService must validate the credential before the backend
            # derives a GuardPrincipal or constructs Central Mind.
            if op == "attach_session":
                if auth_service is None:
                    await websocket.send(json.dumps({
                        "op": "attach_session_result",
                        "ok": False,
                        "error": "authentication service unavailable",
                    }))
                    continue

                presented_token = data.get("token")

                try:
                    candidate_account = auth_service.validate_session(
                        presented_token
                    )

                    candidate_principal = (
                        _guard_principal_from_account(
                            candidate_account
                        )
                    )

                    candidate_guard = GuardLayer(
                        project_root,
                        policy=build_production_guard_policy(),
                        effect_policy=build_production_effect_policy(),
                    )

                    candidate_chatbox = AppChatbox(websocket)

                    candidate_mind, candidate_lock = resolve_mind(
                        presented_token,
                        project_root=project_root,
                        chatbox=candidate_chatbox,
                        guards=candidate_guard,
                        principal=candidate_principal,
                    )

                except AuthenticationError as exc:
                    await websocket.send(json.dumps({
                        "op": "attach_session_result",
                        "ok": False,
                        "error": str(exc),
                    }))
                    continue

                except Exception as exc:
                    await websocket.send(json.dumps({
                        "op": "attach_session_result",
                        "ok": False,
                        "error": (
                            "Central Mind initialization failed: "
                            + str(exc)
                        ),
                    }))
                    continue

                session_token = presented_token
                account = candidate_account
                chatbox = candidate_chatbox
                mind = candidate_mind
                operation_lock = candidate_lock
                if runtimes is not None:
                    runtimes.subscribe(session_token, websocket)

                await websocket.send(json.dumps({
                    "op": "attach_session_result",
                    "ok": True,
                    "account": account,
                }))
                continue

            # ---- logout ----------------------------------------------------
            if op == "logout":
                if auth_service is not None and session_token:
                    auth_service.logout(session_token)
                    if runtimes is not None:
                        runtimes.forget(session_token)

                session_token = None
                account = None
                chatbox = None
                mind = None

                await websocket.send(json.dumps({
                    "op": "logout_result",
                    "ok": True,
                }))
                continue

            # ---- mandatory authentication boundary ------------------------
            #
            # Everything below this point is protected.  Client-supplied
            # role/actor/approved_by fields have no authority.  The backend
            # revalidates its own issued session on EVERY request, so a newer
            # login immediately revokes authority from an older open socket.
            if auth_service is None or not session_token:
                await websocket.send(json.dumps({
                    "op": "auth_required",
                    "ok": False,
                    "error": "authentication required",
                }))
                continue

            try:
                account = auth_service.validate_session(session_token)

                refreshed_principal = (
                    _guard_principal_from_account(account)
                )

                if mind is not None:
                    mind.principal = refreshed_principal

                    # Keep the Broker's trusted identity synchronized with
                    # backend session revalidation on every protected request.
                    if getattr(mind.broker, "guard", None) is not None:
                        mind.broker.principal = refreshed_principal

            except AuthenticationError:
                session_token = None
                account = None
                chatbox = None
                mind = None
                await websocket.send(json.dumps({
                    "op": "auth_required",
                    "ok": False,
                    "error": "session invalid, expired, or revoked",
                }))
                continue

            if mind is None or chatbox is None:
                # This state should never occur after a valid login.  Fail
                # closed instead of constructing privileged state implicitly.
                await websocket.send(json.dumps({
                    "op": "auth_required",
                    "ok": False,
                    "error": "authenticated application state unavailable",
                }))
                continue

            # ---- Administrator account creation ----------------------------
            #
            # Authority comes only from the server-held session_token.
            # Client-supplied role/actor/admin_token/approved_by fields are
            # deliberately ignored.
            async with operation_lock:
                try:
                    account = auth_service.validate_session(session_token)
                except AuthenticationError:
                    await websocket.send(json.dumps({"op": "auth_required", "ok": False, "error": "Session expired or revoked."}))
                    continue
                mind.chatbox = chatbox
                if hasattr(mind, "questioner"):
                    mind.questioner.chatbox = chatbox
                if op == "create_account":
                    try:
                        created = auth_service.create_account(
                            session_token,
                            data.get("username"),
                            data.get("password"),
                            role=data.get("account_role", "user"),
                        )
                    except (AuthenticationError, ValueError) as exc:
                        await websocket.send(json.dumps({
                            "op": "create_account_result",
                            "ok": False,
                            "error": str(exc),
                        }))
                        continue

                    await websocket.send(json.dumps({
                        "op": "create_account_result",
                        "ok": True,
                        "account": created,
                    }))
                    continue

                # ---- gated proposals: list (read-only) ------------------------
                #
                # D018 / D019: gated proposals are NEVER executed by the runtime.
                # proposal_list is read-only. proposal_decide records only.
                # Execution is exclusively an Administrator action, performed
                # OUTSIDE the runtime.
                if op == "proposal_list":
                    if account is None or account.get("role") != "administrator":
                        await websocket.send(json.dumps({
                            "op": "proposal_list_result", "ok": False,
                            "error": "administrator role required",
                        }))
                        continue
                    q = getattr(mind, "proposal_queue", None)
                    rows = q.list(status=data.get("status")) if q is not None else []
                    await websocket.send(json.dumps({
                        "op": "proposal_list_result", "ok": True, "proposals": rows,
                    }))
                    continue

                if op == "proposal_decide":
                    if account is None or account.get("role") != "administrator":
                        await websocket.send(json.dumps({
                            "op": "proposal_decide_result", "ok": False,
                            "error": "administrator role required",
                        }))
                        continue
                    pid = str(data.get("proposal_id") or "").strip()
                    dec = str(data.get("decision") or "").strip().lower()
                    why = str(data.get("reason") or "").strip()
                    if not pid or not dec or not why:
                        await websocket.send(json.dumps({
                            "op": "proposal_decide_result", "ok": False,
                            "error": "proposal_id, decision, reason required",
                        }))
                        continue
                    q = getattr(mind, "proposal_queue", None)
                    if q is None:
                        await websocket.send(json.dumps({
                            "op": "proposal_decide_result", "ok": False,
                            "error": "queue unavailable",
                        }))
                        continue
                    try:
                        updated = q.record_decision(
                            pid, decision=dec,
                            actor=str(account.get("username") or "admin"),
                            reason=why)
                    except Exception as exc:
                        await websocket.send(json.dumps({
                            "op": "proposal_decide_result", "ok": False,
                            "error": str(exc),
                        }))
                        continue
                    try:
                        auth_service._audit_committed(
                            "proposal_decision_recorded",
                            actor=str(account.get("username") or "admin"),
                            subject=pid,
                            detail={"decision": dec, "reason": why})
                    except Exception:
                        pass
                    await websocket.send(json.dumps({
                        "op": "proposal_decide_result", "ok": True, "proposal": updated,
                    }))
                    continue

                # ---- inventory ------------------------------------------------
                if op == "inventory":
                    print("[server] inventory requested")
                    domains = []
                    for organ in mind.inventory.all():
                        if organ.kind != "domain":
                            continue
                        m = organ.manifest or {}
                        domains.append({
                            "name": organ.name,
                            "kind": organ.kind,
                            "display_name": m.get("display_name", organ.name.title()),
                            "icon": m.get("icon", "🔷"),
                            "window": m.get("window", "chat"),
                        })
                    await websocket.send(json.dumps({
                        "op": "inventory_result",
                        "domains": domains,
                    }))
                    continue

                # ---- chats ----------------------------------------------------
                if op == "list_chats":
                    print("[server] list_chats requested")
                    runtime = ChatRuntime(
                        mind,
                        project_root,
                    )
                    chats = runtime.list_chats()
                    print(f"[server] sending {len(chats)} chats")
                    await websocket.send(json.dumps({
                        "op": "chats_result",
                        "chats": chats,
                    }))
                    continue

                # ---- load_chat ------------------------------------------------
                if op == "load_chat":
                    requested_chat_id = str(
                        data.get("chat_id") or ""
                    ).strip()

                    if not requested_chat_id:
                        await websocket.send(json.dumps({
                            "op": "chat_loaded",
                            "ok": False,
                            "error": "chat_id is required",
                        }))
                        continue

                    runtime = ChatRuntime(
                        mind,
                        project_root,
                    )
                    chat = runtime.load_chat(requested_chat_id)

                    if chat is None:
                        await websocket.send(json.dumps({
                            "op": "chat_loaded",
                            "ok": False,
                            "chat_id": requested_chat_id,
                            "error": "chat not found",
                        }))
                        continue

                    await websocket.send(json.dumps({
                        "op": "chat_loaded",
                        "ok": True,
                        **chat,
                    }))
                    continue

                # ---- intake_propose -------------------------------------------
                if op == "intake_propose":
                    path = (data.get("path") or "").strip()
                    print(f"[server] intake_propose: {path}")
                    if not path:
                        await websocket.send(json.dumps({
                            "op": "intake_proposal",
                            "error": "path is required",
                        }))
                        continue

                    try:
                        result = mind.broker.bind_central_mind().call("intake_propose", {
                            "path": path,
                            "caller": mind.caller,
                        })
                    except Exception as e:
                        await websocket.send(json.dumps({
                            "op": "intake_proposal",
                            "error": f"tool failed: {e}",
                        }))
                        continue

                    if not result.get("ok"):
                        await websocket.send(json.dumps({
                            "op": "intake_proposal",
                            "error": result.get("error", "unknown error"),
                        }))
                        continue

                    # Read the proposal from disk (the tool stored it there).
                    pending_path = mind.workspace_root / ".central_mind" / "intake_pending.json"
                    proposal = {}
                    if pending_path.exists():
                        try:
                            proposal = json.loads(pending_path.read_text(encoding="utf-8"))
                        except Exception:
                            proposal = {}

                    await websocket.send(json.dumps({
                        "op": "intake_proposal",
                        "proposal": {
                            "source_path": proposal.get("source_path"),
                            "source_kind": proposal.get("source_kind"),
                            "memory_class": proposal.get("memory_class", "raw"),
                            "domain": proposal.get("domain", "Gen"),
                            "kind": proposal.get("kind", "fact"),
                            "title": proposal.get("title", ""),
                            "tags": proposal.get("tags", []),
                            "content_bytes": len(proposal.get("content", "")),
                            "preview": proposal.get("content", "")[:500],
                        },
                    }))
                    continue

                # ---- intake_commit --------------------------------------------
                if op == "intake_commit":
                    print("[server] intake_commit")
                    proposal = data.get("proposal") or {}

                    if not proposal.get("content"):
                        await websocket.send(json.dumps({
                            "op": "intake_proposal_submitted",
                            "error": "proposal has no content",
                        }))
                        continue

                    memory_service = getattr(mind, "memory_service", None)
                    if memory_service is None:
                        await websocket.send(json.dumps({
                            "op": "intake_proposal_submitted",
                            "error": "shared memory service is not loaded",
                        }))
                        continue

                    try:
                        intake_memory = memory_service.client(
                            actor="intake",
                            role="tool",
                            domain="Gen",
                        )
                        result = mind.broker.bind_central_mind().call("intake_commit", {
                            "proposal": proposal,
                            "memory_bridge": intake_memory,
                        })
                    except Exception as e:
                        await websocket.send(json.dumps({
                            "op": "intake_proposal_submitted",
                            "error": f"tool failed: {e}",
                        }))
                        continue

                    if not result.get("ok"):
                        await websocket.send(json.dumps({
                            "op": "intake_proposal_submitted",
                            "error": result.get("error", "unknown error"),
                        }))
                        continue

                    data_out = result.get("data") or {}
                    proposal_id = data_out.get("proposal_id")
                    if type(proposal_id) is not int:
                        await websocket.send(json.dumps({
                            "op": "intake_proposal_submitted",
                            "error": "intake submission returned an invalid proposal ID",
                        }))
                        continue

                    try:
                        learned = mind.learn_memory_proposal(proposal_id)
                    except Exception as e:
                        await websocket.send(json.dumps({
                            "op": "intake_proposal_submitted",
                            "proposal_id": proposal_id,
                            "status": "pending",
                            "error": f"learning decision failed: {e}",
                        }))
                        continue

                    await websocket.send(json.dumps({
                        "op": "intake_proposal_submitted",
                        "proposal_id": proposal_id,
                        "status": learned.get("status"),
                        "memory_id": learned.get("memory_id"),
                        "memory_class": learned.get("approved_class"),
                        "decision": learned.get("decision"),
                        "decision_reason": learned.get("decision_reason"),
                        "domain": data_out.get("domain", "Gen"),
                        "title": data_out.get("title", ""),
                        "tags": data_out.get("tags", []),
                    }))
                    continue

                # ---- memory review: fail closed pending trusted workflow -------
                #
                # Authentication is already established above. Review remains
                # unavailable because the trusted Administrator/Trainer approval
                # workflow has not yet been integrated with Memory Service.
                # Client-supplied role/actor/approved_by fields never grant it.
                if op == "memory_review_list":
                    await websocket.send(json.dumps({
                        "op": "memory_review_result",
                        "ok": False,
                        "error": (
                            "memory review is disabled until the trusted "
                            "Administrator/Trainer approval workflow is integrated"
                        ),
                        "proposals": [],
                    }))
                    continue

                if op == "memory_review_decide":
                    await websocket.send(json.dumps({
                        "op": "memory_review_decision",
                        "ok": False,
                        "error": (
                            "memory decisions are disabled until the trusted "
                            "Administrator/Trainer approval workflow is integrated"
                        ),
                    }))
                    continue

                # ---- generic application/domain boundary ------------------------
                #
                # The server authenticates the application connection and forwards
                # a generic domain envelope. Domain-specific operation semantics
                # remain entirely behind the domain plug.
                if op == "domain_request":
                    try:
                        from mind.resource_socket import ResourceRequirement

                        component = str(
                            data.get("component") or ""
                        ).strip()
                        capability = str(
                            data.get("capability") or "application"
                        ).strip()

                        if not component:
                            raise ValueError(
                                "domain component is required"
                            )

                        payload = data.get("payload") or {}
                        if not isinstance(payload, dict):
                            raise ValueError(
                                "domain payload must be a mapping"
                            )

                        domain_response = await asyncio.to_thread(
                            mind.resource_socket.request,
                            ResourceRequirement(
                                kind="domain",
                                domain=component,
                                capability=capability,
                            ),
                            request={
                                "mode": "application",
                                "operation": data.get("operation"),
                                "payload": payload,
                            },
                            cognitive_plan={},
                        )

                        await websocket.send(json.dumps({
                            "op": "domain_result",
                            "request_id": data.get("request_id"),
                            "component": component,
                            "operation": data.get("operation"),
                            "ok": (
                                isinstance(domain_response, dict)
                                and domain_response.get("status") == "ok"
                            ),
                            "result": (
                                domain_response.get("result")
                                if isinstance(domain_response, dict)
                                else None
                            ),
                            "error": (
                                domain_response.get("error")
                                if isinstance(domain_response, dict)
                                else "domain returned an invalid response"
                            ),
                        }))
                    except Exception as exc:
                        await websocket.send(json.dumps({
                            "op": "domain_result",
                            "request_id": data.get("request_id"),
                            "component": data.get("component"),
                            "operation": data.get("operation"),
                            "ok": False,
                            "result": None,
                            "error": str(exc),
                        }))
                    continue

                # ---- list files -----------------------------------------------
                if op == "list_files":
                    rel = data.get("path", "")
                    print(f"[server] list_files: {rel!r}")

                    try:
                        result = mind.broker.bind_central_mind().call(
                            "list_files",
                            {"path": rel},
                        )
                    except Exception as e:
                        result = {
                            "ok": False,
                            "data": None,
                            "error": f"tool failed: {e}",
                        }

                    if not result.get("ok"):
                        await websocket.send(json.dumps({
                            "op": "files_result",
                            "path": rel,
                            "error": result.get("error", "unknown error"),
                            "files": [],
                        }))
                        continue

                    files = result.get("data") or []

                    print(
                        f"[server] list_files done: "
                        f"{len(files) if isinstance(files, list) else 0} entries"
                    )

                    await websocket.send(json.dumps({
                        "op": "files_result",
                        "path": rel,
                        "files": files,
                    }))
                    continue

                # ---- read file ------------------------------------------------
                if op == "read_file":
                    rel = data.get("path", "")
                    print(f"[server] read_file: {rel}")

                    try:
                        result = mind.broker.bind_central_mind().call(
                            "read_file",
                            {"path": rel},
                        )
                    except Exception as e:
                        result = {
                            "ok": False,
                            "data": None,
                            "error": f"tool failed: {e}",
                        }

                    if not result.get("ok"):
                        await websocket.send(json.dumps({
                            "op": "file_content",
                            "path": rel,
                            "error": result.get("error", "unknown error"),
                            "content": "",
                        }))
                        continue

                    await websocket.send(json.dumps({
                        "op": "file_content",
                        "path": rel,
                        "content": result.get("data") or "",
                    }))
                    continue

                # ---- chat message ---------------------------------------------
                text = data.get("text", "").strip()
                intent = data.get("intent", "ask")
                if not text:
                    continue

                print(f"[server] << [{intent}] {text}")

                try:
                    chatbox.tool_status(f"Thinking ({intent})...")
                    mind.broker.reset_budget()

                    attachments = data.get("attachments") or []
                    requested_chat_id = data.get("chat_id")

                    runtime = ChatRuntime(
                        mind,
                        project_root,
                    )

                    requested_chat = runtime.open_chat(requested_chat_id)
                    requested_chat_id = requested_chat.chat_id
                    await websocket.send(json.dumps({
                        "op": "turn_started", "request_id": data.get("request_id"),
                        "chat_id": requested_chat_id,
                    }))
                    result = await asyncio.to_thread(
                        runtime.respond,
                        text,
                        chat_id=requested_chat_id,
                        intent=intent,
                        attachments=attachments,
                        context=data.get("context") if isinstance(data.get("context"), dict) else None,
                    )

                    if result.get("ok") and result.get("artifacts") and runtimes is not None:
                        await runtimes.publish(session_token, {"op": "artifacts_changed", "artifacts": result["artifacts"]})
                    if result.get("ok"):
                        await websocket.send(json.dumps({
                            "role": "mind",
                            "request_id": data.get("request_id"),
                            "status": result.get("status"),
                            "questions": result.get("questions", []),
                            "artifacts": result.get("artifacts", []),
                            "text": result.get("text", ""),
                            "chat_id": result.get("chat_id"),
                            "domain": result.get("domain"),
                            "capability": result.get("capability"),
                            "source_model": result.get("source_model"),
                            "source_llm": result.get("source_llm"),
                            "provider": result.get("provider"),
                            "execution_model": result.get("execution_model"),
                            "memory_ids": result.get("memory_ids", []),
                        }))
                    else:
                        await websocket.send(json.dumps({
                            "role": "mind",
                            "request_id": data.get("request_id"),
                            "status": "error",
                            "text": (
                                "[mind error] "
                                + result.get(
                                    "error",
                                    "Chat Runtime failed",
                                )
                            ),
                            "chat_id": result.get("chat_id"),
                            "domain": result.get("domain"),
                            "capability": result.get("capability"),
                            "attempts": result.get("attempts", []),
                        }))

                except Exception as exc:
                    await websocket.send(json.dumps({
                        "role": "mind",
                        "text": f"[mind error] {exc}", "status": "error",
                        "request_id": data.get("request_id"),
                    }))
    except Exception as exc:
        print(f"[server] client error: {exc}")
    finally:
        if runtimes is not None:
            runtimes.unsubscribe(websocket)
        print(f"[server] client disconnected")


async def main_async(
    project_root: Path,
    *,
    app_owner_pid: int | None = None,
    app_runtime_token: str | None = None,
):
    try:
        import websockets
    except ImportError:
        print("[server] websockets library not installed.")
        print("[server] Install with: pip3 install websockets")
        sys.exit(1)

    auth_service = AuthService(_default_auth_database())
    runtimes = SessionRuntimes(auth_service)

    async def handler(ws):
        await handle_client(
            ws,
            project_root,
            auth_service=auth_service,
            runtimes=runtimes,
        )

    print(f"[server] listening on ws://{HOST}:{PORT}")

    async with websockets.serve(handler, HOST, PORT):
        if app_owner_pid is None:
            # Standalone development mode: no Section 0 owner.
            await asyncio.Future()
        else:
            if app_runtime_token is None:
                raise RuntimeError(
                    "owned server requires an app runtime token"
                )

            await _watch_app_owner(
                app_owner_pid,
                app_runtime_token,
            )


def run_server(
    project_root: Path,
    *,
    app_owner_pid: int | None = None,
    app_runtime_token: str | None = None,
):
    asyncio.run(
        main_async(
            project_root,
            app_owner_pid=app_owner_pid,
            app_runtime_token=app_runtime_token,
        )
    )