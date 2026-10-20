import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CENTRAL_MIND_DIR = PROJECT_ROOT / "section_1_central_mind"
sys.path.insert(0, str(CENTRAL_MIND_DIR))

import server


ADMIN_USER = "security_admin"
ADMIN_PASSWORD = "A-long-test-password-1"


class FakeWebSocket:
    def __init__(self, messages):
        self.messages = [json.dumps(m) for m in messages]
        self.sent = []

    def __aiter__(self):
        self._iterator = iter(self.messages)
        return self

    async def __anext__(self):
        try:
            return next(self._iterator)
        except StopIteration:
            raise StopAsyncIteration

    async def send(self, message):
        self.sent.append(json.loads(message))


class FakeInventory:
    def all(self):
        return []


class FakeBroker:
    def reset_budget(self):
        pass


class SafeFakeMind:
    constructions = 0

    def __init__(self, **kwargs):
        type(self).constructions += 1
        self.guards = kwargs.get("guards")
        self.principal = kwargs.get("principal")
        self.inventory = FakeInventory()
        self.broker = FakeBroker()
        self.memory_service = None
        self.caller = None
        self.workspace_root = PROJECT_ROOT


class ServerAuthenticationSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.auth = server.AuthService(
            Path(self.temp.name) / "private" / "auth.sqlite3"
        )
        self.auth.bootstrap_admin(ADMIN_USER, ADMIN_PASSWORD)
        SafeFakeMind.constructions = 0

    def tearDown(self):
        self.temp.cleanup()

    def run_client(self, messages, mind=SafeFakeMind):
        ws = FakeWebSocket(messages)
        with patch.object(server, "CentralMind", mind):
            asyncio.run(
                server.handle_client(
                    ws,
                    PROJECT_ROOT,
                    auth_service=self.auth,
                )
            )
        return ws.sent

    @staticmethod
    def messages_with_op(sent, op):
        return [m for m in sent if m.get("op") == op]

    def assert_auth_required(self, sent):
        matches = self.messages_with_op(sent, "auth_required")
        self.assertTrue(matches, sent)
        self.assertFalse(matches[-1]["ok"])

    def test_no_central_mind_before_authentication(self):
        sent = self.run_client([
            {"op": "inventory"},
        ])
        self.assert_auth_required(sent)
        self.assertEqual(SafeFakeMind.constructions, 0)

    def test_unauthenticated_inventory_is_denied(self):
        sent = self.run_client([{"op": "inventory"}])
        self.assert_auth_required(sent)

    def test_unauthenticated_file_listing_is_denied(self):
        sent = self.run_client([
            {"op": "list_files", "path": ""},
        ])
        self.assert_auth_required(sent)

    def test_unauthenticated_file_read_is_denied(self):
        sent = self.run_client([
            {
                "op": "read_file",
                "path": "section_1_central_mind/server.py",
            },
        ])
        self.assert_auth_required(sent)

    def test_unauthenticated_intake_is_denied(self):
        sent = self.run_client([
            {
                "op": "intake_commit",
                "proposal": {"content": "hostile"},
            },
        ])
        self.assert_auth_required(sent)

    def test_authenticated_intake_commit_invokes_central_learning_decision(self):
        captured = {
            "broker_calls": [],
            "learn_calls": [],
        }

        class IntakeMemoryService:
            def client(self, *, actor, role, domain):
                captured["memory_client_request"] = {
                    "actor": actor,
                    "role": role,
                    "domain": domain,
                }
                return "trusted-intake-memory-client"

        class BoundIntakeBroker:
            def call(self, operation, args):
                captured["broker_calls"].append({
                    "operation": operation,
                    "args": args,
                })
                self_test.assertEqual(operation, "intake_commit")
                self_test.assertEqual(
                    args["memory_bridge"],
                    "trusted-intake-memory-client",
                )
                return {
                    "ok": True,
                    "data": {
                        "proposal_id": 73,
                        "status": "pending",
                        "domain": "Gen",
                        "title": "Imported knowledge",
                        "tags": ["intake"],
                    },
                    "error": None,
                }

        class IntakeBroker:
            def reset_budget(self):
                pass

            def bind_central_mind(self):
                captured["bound_central_mind"] = True
                return BoundIntakeBroker()

        class IntakeMind(SafeFakeMind):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.memory_service = IntakeMemoryService()
                self.broker = IntakeBroker()

            def learn_memory_proposal(self, proposal_id):
                captured["learn_calls"].append(proposal_id)
                return {
                    "proposal_id": proposal_id,
                    "status": "approved",
                    "memory_id": "mem-73",
                    "approved_class": "tested",
                    "decision": "approve",
                    "decision_reason": "explicit testable knowledge passed",
                }

        self_test = self
        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
            {
                "op": "intake_commit",
                "proposal": {
                    "content": "verified imported knowledge",
                    "domain": "Gen",
                    "title": "Imported knowledge",
                    "tags": ["intake"],
                },
            },
        ], mind=IntakeMind)

        login = self.messages_with_op(sent, "login_result")
        self.assertEqual(len(login), 1, sent)
        self.assertTrue(login[0]["ok"], sent)

        result = self.messages_with_op(
            sent,
            "intake_proposal_submitted",
        )
        self.assertEqual(len(result), 1, sent)
        self.assertNotIn("error", result[0], sent)

        self.assertTrue(captured.get("bound_central_mind"))
        self.assertEqual(
            captured.get("memory_client_request"),
            {
                "actor": "intake",
                "role": "tool",
                "domain": "Gen",
            },
        )
        self.assertEqual(len(captured["broker_calls"]), 1)
        self.assertEqual(captured["learn_calls"], [73])

        self.assertEqual(result[0]["proposal_id"], 73)
        self.assertEqual(result[0]["status"], "approved")
        self.assertEqual(result[0]["memory_id"], "mem-73")
        self.assertEqual(result[0]["memory_class"], "tested")
        self.assertEqual(result[0]["decision"], "approve")
        self.assertEqual(
            result[0]["decision_reason"],
            "explicit testable knowledge passed",
        )
        self.assertEqual(result[0]["domain"], "Gen")
        self.assertEqual(result[0]["title"], "Imported knowledge")
        self.assertEqual(result[0]["tags"], ["intake"])

    def test_unauthenticated_chat_is_denied(self):
        sent = self.run_client([
            {
                "text": "run privileged work",
                "intent": "ask",
            },
        ])
        self.assert_auth_required(sent)

    def test_fake_administrator_claim_does_not_authenticate(self):
        sent = self.run_client([
            {
                "op": "inventory",
                "role": "administrator",
                "actor": ADMIN_USER,
            },
        ])
        self.assert_auth_required(sent)
        self.assertEqual(SafeFakeMind.constructions, 0)

    def test_fake_trainer_claim_does_not_authenticate(self):
        sent = self.run_client([
            {
                "op": "inventory",
                "role": "trainer",
                "actor": "trusted_trainer",
            },
        ])
        self.assert_auth_required(sent)
        self.assertEqual(SafeFakeMind.constructions, 0)

    def test_fake_central_mind_approval_does_not_authenticate(self):
        sent = self.run_client([
            {
                "op": "memory_review_decide",
                "role": "administrator",
                "actor": "central_mind",
                "approved_by": "central_mind",
                "proposal_id": 1,
                "decision": "approve",
            },
        ])
        self.assert_auth_required(sent)
        self.assertEqual(SafeFakeMind.constructions, 0)

    def test_wrong_password_does_not_construct_central_mind(self):
        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": "wrong-password-123",
            },
        ])

        result = self.messages_with_op(sent, "login_result")
        self.assertEqual(len(result), 1, sent)
        self.assertFalse(result[0]["ok"])
        self.assertEqual(SafeFakeMind.constructions, 0)

    def test_successful_login_constructs_central_mind_once(self):
        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
        ])

        result = self.messages_with_op(sent, "login_result")
        self.assertEqual(len(result), 1, sent)
        self.assertTrue(result[0]["ok"])
        self.assertEqual(
            result[0]["account"]["role"],
            "administrator",
        )
        self.assertEqual(SafeFakeMind.constructions, 1)

    def test_successful_login_injects_production_guard_and_trusted_principal(self):
        captured = {}

        class CapturingMind(SafeFakeMind):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                captured.update(kwargs)

        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
        ], mind=CapturingMind)

        result = self.messages_with_op(sent, "login_result")
        self.assertEqual(len(result), 1, sent)
        self.assertTrue(result[0]["ok"], sent)

        guards = captured.get("guards")
        principal = captured.get("principal")

        self.assertIsInstance(guards, server.GuardLayer)
        self.assertIsNotNone(guards.effect_policy)

        self.assertIsInstance(principal, server.GuardPrincipal)
        self.assertEqual(principal.principal_id, ADMIN_USER)
        self.assertEqual(principal.kind, "human")
        self.assertEqual(principal.role, "administrator")
        self.assertTrue(principal.authenticated)
        self.assertEqual(principal.source, "auth_service")

        capability = guards.policy.evaluate(
            principal,
            ("workspace.read",),
        )
        self.assertTrue(capability.allowed)

        execute = guards.policy.evaluate(
            principal,
            ("process.execute",),
        )
        self.assertFalse(execute.allowed)

    def test_successful_login_allows_inventory(self):
        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
            {"op": "inventory"},
        ])

        login = self.messages_with_op(sent, "login_result")
        inventory = self.messages_with_op(sent, "inventory_result")

        self.assertEqual(len(login), 1, sent)
        self.assertTrue(login[0]["ok"])
        self.assertEqual(len(inventory), 1, sent)
        self.assertEqual(inventory[0]["domains"], [])

    def test_unauthenticated_account_creation_is_denied(self):
        sent = self.run_client([
            {
                "op": "create_account",
                "username": "hostile_trainer",
                "password": "A-long-test-password-4",
                "account_role": "trainer",
            },
        ])

        self.assert_auth_required(sent)

        created = self.messages_with_op(
            sent,
            "create_account_result",
        )
        self.assertEqual(created, [])

    def test_fake_administrator_claim_cannot_create_account(self):
        sent = self.run_client([
            {
                "op": "create_account",
                "username": "hostile_trainer",
                "password": "A-long-test-password-4",
                "account_role": "trainer",
                "role": "administrator",
                "actor": ADMIN_USER,
                "approved_by": ADMIN_USER,
                "admin_token": "fake-client-token",
            },
        ])

        self.assert_auth_required(sent)

        with self.assertRaises(server.AuthenticationError):
            self.auth.login(
                "hostile_trainer",
                "A-long-test-password-4",
            )

    def test_authenticated_administrator_can_create_trainer(self):
        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
            {
                "op": "create_account",
                "username": "designated_trainer",
                "password": "A-long-test-password-4",
                "account_role": "trainer",
            },
        ])

        result = self.messages_with_op(
            sent,
            "create_account_result",
        )

        self.assertEqual(len(result), 1, sent)
        self.assertTrue(result[0]["ok"], sent)
        self.assertEqual(
            result[0]["account"]["username"],
            "designated_trainer",
        )
        self.assertEqual(
            result[0]["account"]["role"],
            "trainer",
        )

        trainer = self.auth.login(
            "designated_trainer",
            "A-long-test-password-4",
        )
        self.assertEqual(
            trainer["account"]["role"],
            "trainer",
        )

    def test_client_authority_fields_are_ignored_for_account_creation(self):
        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
            {
                "op": "create_account",
                "username": "ordinary_created",
                "password": "A-long-test-password-5",
                "account_role": "user",
                "role": "trainer",
                "actor": "central_mind",
                "approved_by": "central_mind",
                "admin_token": "hostile-client-token",
            },
        ])

        result = self.messages_with_op(
            sent,
            "create_account_result",
        )

        self.assertEqual(len(result), 1, sent)
        self.assertTrue(result[0]["ok"], sent)
        self.assertEqual(
            result[0]["account"]["role"],
            "user",
        )

        account = self.auth.login(
            "ordinary_created",
            "A-long-test-password-5",
        )
        self.assertEqual(
            account["account"]["role"],
            "user",
        )

    def test_ordinary_user_cannot_create_account(self):
        admin = self.auth.login(
            ADMIN_USER,
            ADMIN_PASSWORD,
        )
        self.auth.create_account(
            admin["token"],
            "ordinary_user",
            "A-long-test-password-2",
            role="user",
        )

        sent = self.run_client([
            {
                "op": "login",
                "username": "ordinary_user",
                "password": "A-long-test-password-2",
            },
            {
                "op": "create_account",
                "username": "forbidden_user",
                "password": "A-long-test-password-3",
                "account_role": "user",
                "role": "administrator",
                "actor": ADMIN_USER,
                "admin_token": admin["token"],
            },
        ])

        result = self.messages_with_op(
            sent,
            "create_account_result",
        )

        self.assertEqual(len(result), 1, sent)
        self.assertFalse(result[0]["ok"], sent)

        with self.assertRaises(server.AuthenticationError):
            self.auth.login(
                "forbidden_user",
                "A-long-test-password-3",
            )

    def test_trainer_cannot_create_account(self):
        admin = self.auth.login(
            ADMIN_USER,
            ADMIN_PASSWORD,
        )
        self.auth.create_account(
            admin["token"],
            "designated_trainer",
            "A-long-test-password-4",
            role="trainer",
        )

        sent = self.run_client([
            {
                "op": "login",
                "username": "designated_trainer",
                "password": "A-long-test-password-4",
            },
            {
                "op": "create_account",
                "username": "forbidden_user",
                "password": "A-long-test-password-3",
                "account_role": "user",
                "role": "administrator",
                "actor": ADMIN_USER,
                "admin_token": admin["token"],
            },
        ])

        result = self.messages_with_op(
            sent,
            "create_account_result",
        )

        self.assertEqual(len(result), 1, sent)
        self.assertFalse(result[0]["ok"], sent)

        with self.assertRaises(server.AuthenticationError):
            self.auth.login(
                "forbidden_user",
                "A-long-test-password-3",
            )

    def test_second_trainer_creation_is_denied(self):
        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
            {
                "op": "create_account",
                "username": "designated_trainer",
                "password": "A-long-test-password-4",
                "account_role": "trainer",
            },
            {
                "op": "create_account",
                "username": "second_trainer",
                "password": "A-long-test-password-5",
                "account_role": "trainer",
            },
        ])

        results = self.messages_with_op(
            sent,
            "create_account_result",
        )

        self.assertEqual(len(results), 2, sent)
        self.assertTrue(results[0]["ok"], sent)
        self.assertFalse(results[1]["ok"], sent)

        with self.assertRaises(server.AuthenticationError):
            self.auth.login(
                "second_trainer",
                "A-long-test-password-5",
            )

    def test_server_denied_second_trainer_is_audited(self):
        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
            {
                "op": "create_account",
                "username": "designated_trainer",
                "password": "A-long-test-password-4",
                "account_role": "trainer",
            },
            {
                "op": "create_account",
                "username": "second_trainer",
                "password": "A-long-test-password-5",
                "account_role": "trainer",
            },
        ])

        results = self.messages_with_op(
            sent,
            "create_account_result",
        )
        self.assertEqual(len(results), 2, sent)
        self.assertFalse(results[-1]["ok"], sent)

        admin = self.auth.login(
            ADMIN_USER,
            ADMIN_PASSWORD,
        )
        events = self.auth.audit_events(
            admin["token"],
            limit=1000,
        )

        denied = [
            event
            for event in events
            if event["event"] == "account_creation_denied"
            and event["subject"] == "second_trainer"
        ]

        self.assertTrue(denied)

    def test_authenticated_memory_review_still_remains_closed(self):
        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
            {
                "op": "memory_review_list",
                "role": "administrator",
            },
        ])

        result = self.messages_with_op(sent, "memory_review_result")
        self.assertEqual(len(result), 1, sent)
        self.assertFalse(result[0]["ok"])
        self.assertEqual(result[0]["proposals"], [])
        self.assertIn(
            "approval workflow",
            result[0]["error"],
        )
        self.assertNotIn(
            "authentication is implemented",
            result[0]["error"],
        )

    def test_logout_removes_connection_authority(self):
        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
            {"op": "logout"},
            {"op": "inventory"},
        ])

        logout = self.messages_with_op(sent, "logout_result")
        self.assertEqual(len(logout), 1, sent)
        self.assertTrue(logout[0]["ok"])
        self.assert_auth_required(sent)

    def test_second_login_revokes_first_open_connection(self):
        class RevokingWebSocket(FakeWebSocket):
            def __init__(self, outer):
                super().__init__([])
                self.outer = outer
                self.stage = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.stage == 0:
                    self.stage = 1
                    return json.dumps({
                        "op": "login",
                        "username": ADMIN_USER,
                        "password": ADMIN_PASSWORD,
                    })

                if self.stage == 1:
                    self.stage = 2

                    # A second login happens while the first WebSocket remains
                    # open.  AuthService's one-active-session rule replaces
                    # the first token.
                    self.outer.auth.login(
                        ADMIN_USER,
                        ADMIN_PASSWORD,
                    )

                    return json.dumps({"op": "inventory"})

                raise StopAsyncIteration

        ws = RevokingWebSocket(self)

        with patch.object(server, "CentralMind", SafeFakeMind):
            asyncio.run(
                server.handle_client(
                    ws,
                    PROJECT_ROOT,
                    auth_service=self.auth,
                )
            )

        login = self.messages_with_op(ws.sent, "login_result")
        self.assertEqual(len(login), 1, ws.sent)
        self.assertTrue(login[0]["ok"])

        self.assert_auth_required(ws.sent)

        inventory = self.messages_with_op(
            ws.sent,
            "inventory_result",
        )
        self.assertEqual(inventory, [])

    def test_missing_auth_service_fails_closed(self):
        ws = FakeWebSocket([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
            {
                "op": "inventory",
                "role": "administrator",
            },
        ])

        with patch.object(
            server,
            "CentralMind",
            side_effect=AssertionError(
                "CentralMind must not be constructed without AuthService"
            ),
        ):
            asyncio.run(
                server.handle_client(
                    ws,
                    PROJECT_ROOT,
                    auth_service=None,
                )
            )

        login = self.messages_with_op(ws.sent, "login_result")
        self.assertEqual(len(login), 1, ws.sent)
        self.assertFalse(login[0]["ok"])
        self.assert_auth_required(ws.sent)

    def test_auth_status_does_not_construct_central_mind(self):
        sent = self.run_client([
            {"op": "auth_status"},
        ])

        result = self.messages_with_op(
            sent,
            "auth_status_result",
        )
        self.assertEqual(len(result), 1, sent)
        self.assertFalse(result[0]["authenticated"])
        self.assertIsNone(result[0]["account"])
        self.assertTrue(result[0]["auth_available"])
        self.assertFalse(result[0]["registration_enabled"])
        self.assertEqual(SafeFakeMind.constructions, 0)

    def test_auth_status_reports_authenticated_after_valid_login(self):
        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
            {"op": "auth_status"},
        ])

        result = self.messages_with_op(
            sent,
            "auth_status_result",
        )
        self.assertEqual(len(result), 1, sent)
        self.assertTrue(result[0]["authenticated"], sent)
        self.assertEqual(
            result[0]["account"]["username"],
            ADMIN_USER,
        )
        self.assertEqual(
            result[0]["account"]["role"],
            "administrator",
        )

    def test_auth_status_reports_unauthenticated_after_logout(self):
        sent = self.run_client([
            {
                "op": "login",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
            {"op": "logout"},
            {"op": "auth_status"},
        ])

        result = self.messages_with_op(
            sent,
            "auth_status_result",
        )
        self.assertEqual(len(result), 1, sent)
        self.assertFalse(result[0]["authenticated"], sent)
        self.assertIsNone(result[0]["account"])

    def test_auth_status_revalidates_and_rejects_revoked_session(self):
        class RevokingStatusWebSocket(FakeWebSocket):
            def __init__(self, outer):
                super().__init__([])
                self.outer = outer
                self.stage = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.stage == 0:
                    self.stage = 1
                    return json.dumps({
                        "op": "login",
                        "username": ADMIN_USER,
                        "password": ADMIN_PASSWORD,
                    })

                if self.stage == 1:
                    self.stage = 2

                    # Replace the first connection's active session while
                    # leaving that WebSocket open.
                    self.outer.auth.login(
                        ADMIN_USER,
                        ADMIN_PASSWORD,
                    )

                    return json.dumps({
                        "op": "auth_status",
                    })

                if self.stage == 2:
                    self.stage = 3

                    # If auth_status correctly cleared stale application
                    # authority, the next protected request must fail before
                    # reaching Central Mind.
                    return json.dumps({
                        "op": "inventory",
                    })

                raise StopAsyncIteration

        ws = RevokingStatusWebSocket(self)

        with patch.object(server, "CentralMind", SafeFakeMind):
            asyncio.run(
                server.handle_client(
                    ws,
                    PROJECT_ROOT,
                    auth_service=self.auth,
                )
            )

        status = self.messages_with_op(
            ws.sent,
            "auth_status_result",
        )
        self.assertEqual(len(status), 1, ws.sent)
        self.assertFalse(status[0]["authenticated"], ws.sent)
        self.assertIsNone(status[0]["account"])

        self.assert_auth_required(ws.sent)

        inventory = self.messages_with_op(
            ws.sent,
            "inventory_result",
        )
        self.assertEqual(inventory, [])


if __name__ == "__main__":
    unittest.main()
