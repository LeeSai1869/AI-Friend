"""Intake tools.

The intake flow:
  1. intake_propose reads a source and asks the chat model to
     propose a classification. Caller is passed in args.
  2. The user reviews and confirms.
  3. intake_commit submits the confirmed proposal to the Memory Service.
     Central Mind evaluates and decides the resulting knowledge proposal.
     Memory client is passed in args.

Dependencies are explicit: caller and memory_bridge come in via
args. The tool never reaches into the broker.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List

from _base.tool import Tool
from guard.contract import ToolEffect


PENDING_FILE = ".central_mind/intake_pending.json"


class IntakePropose(Tool):
    name = "intake_propose"
    description = (
        "Read a source and propose a classification for raw memory. "
        "Does NOT write. The proposal is stored for later confirmation."
    )
    parameters = {
        "path": "file or folder path (relative to workspace root)",
        "caller": "the mind's model caller (passed by the mind)",
    }

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        rel = (args.get("path") or "").strip()
        if not rel:
            raise ValueError("path is required")

        if Path(rel).is_absolute():
            target = Path(rel).resolve()
            try:
                target.relative_to(self.workspace_root)
            except ValueError:
                raise ValueError(
                    f"path is outside the workspace: {rel}"
                )
        else:
            target = self._resolve(rel)

        read_scope = (
            "tree"
            if target.exists() and target.is_dir()
            else "exact"
        )

        pending = (
            self.workspace_root / PENDING_FILE
        ).resolve()

        pending_action = (
            "write"
            if pending.exists()
            else "create"
        )

        return (
            ToolEffect(
                action="read",
                target=str(target),
                scope=read_scope,
            ),
            ToolEffect(
                action="service",
                target="model:chat",
                scope="service",
            ),
            ToolEffect(
                action=pending_action,
                target=str(pending),
                scope="exact",
            ),
        )

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rel = (args.get("path") or "").strip()
        caller = args.get("caller")

        if not rel:
            return {"ok": False, "data": None, "error": "path is required"}
        if caller is None:
            return {"ok": False, "data": None, "error": "caller is required"}

        # Accept absolute paths inside the workspace by converting them
        # to relative paths. Reject anything outside.
        if Path(rel).is_absolute():
            try:
                rel = str(Path(rel).resolve().relative_to(self.workspace_root))
            except ValueError:
                return {
                    "ok": False,
                    "data": None,
                    "error": f"path is outside the workspace: {rel}",
                }

        try:
            target = self._resolve(rel)
        except ValueError as e:
            return {"ok": False, "data": None, "error": str(e)}

        if not target.exists():
            return {"ok": False, "data": None, "error": f"not found: {rel}"}

        # Read content.
        if target.is_file():
            try:
                content = target.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                return {"ok": False, "data": None, "error": f"read failed: {e}"}
            source_kind = "file"
        else:
            files = sorted(
                p for p in target.rglob("*")
                if p.is_file()
                and not any(part.startswith(".") for part in p.parts)
                and "__pycache__" not in p.parts
            )[:50]
            chunks = [f"Folder: {rel}", f"File count: {len(files)}", ""]
            for f in files:
                try:
                    sub = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                chunks.append(f"----- {f.relative_to(self.workspace_root)} -----")
                chunks.append(sub[:2000])
                chunks.append("")
            content = "\n".join(chunks)
            source_kind = "folder"

        preview = content[:6000]

        # Ask the chat model to classify.
        prompt = (
            "You are classifying source material before it is stored in\n"
            "the mind's raw memory.\n\n"
            f"Source: {rel}\n"
            f"Kind: {source_kind}\n\n"
            f"Content preview:\n{preview}\n\n"
            "Reply with ONLY a JSON object in this shape:\n"
            "{\n"
            '  "domain": "Cod" | "Img" | "Vid" | "Trd" | "Gen" | "Mind" | "Chr" | "Cap",\n'
            '  "title": "short one-line description",\n'
            '  "tags": ["tag1", "tag2", ...],\n'
            '  "kind": "language" | "formula" | "pattern" | "fact" | "observation"\n'
            "}\n\n"
            "No prose. Only JSON."
        )

        try:
            reply = caller.call(
                "chat",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            return {"ok": False, "data": None, "error": f"model failed: {e}"}

        proposal: Dict[str, Any] = {}
        try:
            proposal = json.loads(reply)
        except Exception:
            m = re.search(r"\{.*\}", reply, re.DOTALL)
            if m:
                try:
                    proposal = json.loads(m.group(0))
                except Exception:
                    proposal = {}

        if not proposal:
            return {
                "ok": False,
                "data": None,
                "error": f"model did not produce JSON: {reply[:200]}",
            }

        proposal.setdefault("domain", "Gen")
        proposal.setdefault("title", Path(rel).name)
        proposal.setdefault("tags", [])
        proposal.setdefault("kind", "fact")

        proposal["source_path"] = rel
        proposal["source_kind"] = source_kind
        proposal["content"] = content
        proposal["originator"] = [{"type": "trainer", "name": "user"}]
        proposal["created_at"] = time.time()
        proposal["memory_class"] = "raw"

        # Persist pending proposal.
        pending_path = self.workspace_root / PENDING_FILE
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        pending_path.write_text(
            json.dumps(proposal, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return {
            "ok": True,
            "data": {
                "proposal": {
                    "source_path": proposal["source_path"],
                    "source_kind": proposal["source_kind"],
                    "memory_class": proposal["memory_class"],
                    "domain": proposal["domain"],
                    "kind": proposal["kind"],
                    "title": proposal["title"],
                    "tags": proposal["tags"],
                    "content_bytes": len(content),
                    "preview": content[:500],
                },
            },
            "error": None,
        }


class IntakeCommit(Tool):
    name = "intake_commit"
    description = "Submit a confirmed intake proposal for Central Mind learning."
    parameters = {
        "proposal": "the proposal dict from intake_propose, possibly edited",
        "memory_bridge": "the Memory Service client (passed by the mind)",
    }

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        proposal = args.get("proposal") or {}
        if not proposal.get("content"):
            raise ValueError("proposal has no content")

        return (
            ToolEffect(
                action="memory",
                target="memory:knowledge_proposal",
                scope="service",
            ),
        )

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        proposal = args.get("proposal") or {}
        bridge = args.get("memory_bridge")

        if not proposal.get("content"):
            return {"ok": False, "data": None, "error": "proposal has no content"}
        if bridge is None:
            return {"ok": False, "data": None, "error": "memory_bridge is required"}

        source_path = proposal.get("source_path")
        try:
            submitted = bridge.propose_knowledge(
                domain=proposal.get("domain", "Gen"),
                title=proposal.get("title", source_path or "intake"),
                content=proposal.get("content", ""),
                originator=proposal.get("originator")
                    or [{"type": "trainer", "name": "user"}],
                tags=list(proposal.get("tags") or []),
                kind=proposal.get("kind", "fact"),
                requested_class="raw",
                source_refs=[source_path] if source_path else [],
                source={
                    "source_type": "intake",
                    "source_path": source_path,
                    "source_kind": proposal.get("source_kind"),
                },
                evidence={
                    "content_bytes": len(proposal.get("content", "")),
                    "preview_available": bool(proposal.get("preview")),
                    "imported_source": True,
                },
                derivation_note=(
                    "Imported source submitted for Central Mind review; "
                    "not yet approved or stored as a memory entry."
                ),
            )
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": f"proposal submission failed: {e}",
            }

        proposal_id = submitted.get("proposal_id")
        if proposal_id is None:
            return {
                "ok": False,
                "data": None,
                "error": "proposal service returned no proposal ID",
            }

        # Preserve the pending intake file for recovery and review.
        return {
            "ok": True,
            "data": {
                "proposal_id": proposal_id,
                "status": submitted.get("status", "pending"),
                "domain": proposal.get("domain", "Gen"),
                "title": proposal.get("title", ""),
                "tags": proposal.get("tags", []),
            },
            "error": None,
        }


TOOLS = [IntakePropose, IntakeCommit]
