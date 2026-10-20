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


class ForbiddenMemoryService:
    def pending_knowledge_proposals(self):
        raise AssertionError("Protected proposal listing was reached")

    def __getattr__(self, name):
        raise AssertionError(f"Unexpected memory service access: {name}")


class FakeCentralMind:
    def __init__(self, **kwargs):
        self.memory_service = ForbiddenMemoryService()
        self.inventory = None
        self.broker = None

    def decide_memory_proposal(self, *args, **kwargs):
        raise AssertionError("Protected decision method was reached")


class MemoryReviewDispatchSecurityTests(unittest.TestCase):
    def run_dispatch(self, message):
        # These tests deliberately do NOT log in.  Even convincing client
        # claims such as role=administrator or approved_by=central_mind must
        # be stopped before CentralMind or protected memory is reached.
        websocket = FakeWebSocket([message])

        with tempfile.TemporaryDirectory() as temp:
            auth = server.AuthService(
                Path(temp) / "private" / "auth.sqlite3"
            )
            auth.bootstrap_admin(
                "test_admin",
                "A-long-test-password-1",
            )

            with patch.object(
                server,
                "CentralMind",
                side_effect=AssertionError(
                    "CentralMind constructed before authentication"
                ),
            ):
                asyncio.run(
                    server.handle_client(
                        websocket,
                        PROJECT_ROOT,
                        auth_service=auth,
                    )
                )

        return websocket.sent

    def response_for(self, sent, operation):
        matches = [item for item in sent if item.get("op") == operation]
        self.assertEqual(len(matches), 1, sent)
        return matches[0]

    def test_list_denied_even_when_client_claims_trainer_role(self):
        sent = self.run_dispatch({
            "op": "memory_review_list",
            "role": "trainer",
            "actor": "trusted_trainer",
        })
        response = self.response_for(sent, "auth_required")
        self.assertFalse(response["ok"])
        self.assertIn("authentication", response["error"])

    def test_decision_denied_even_when_client_claims_admin_role(self):
        sent = self.run_dispatch({
            "op": "memory_review_decide",
            "role": "administrator",
            "approved_by": "central_mind",
            "proposal_id": 1,
            "decision": "approve",
            "reason": "test approval",
            "memory_class": "tested",
        })
        response = self.response_for(sent, "auth_required")
        self.assertFalse(response["ok"])
        self.assertIn("authentication", response["error"])


if __name__ == "__main__":
    unittest.main()
