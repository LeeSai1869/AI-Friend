from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

from section_1_central_mind.guard.contract import GuardPrincipal
from section_1_central_mind.guard.layer import GuardLayer
from section_1_central_mind.guard.production_policy import (
    build_production_effect_policy,
    build_production_guard_policy,
)
from section_1_central_mind.mind.broker import ToolBroker
from section_1_central_mind.mind.inventory import Inventory
from section_1_central_mind.mind.verifier import Verifier
from section_1_central_mind.mind.appraiser import SelfAppraiser


class DeterministicCoderCaller:
    """Deterministic model boundary for the Coding V1 integration test."""

    def __init__(self):
        self.calls = []
        self.last_source = {
            "type": "model",
            "name": "deterministic-coder-test",
            "capability": "write",
            "organ": "coding",
        }

    def route(self, domain, capability, messages, max_tokens=2048, structured_output=None):
        self.calls.append({
            "domain": domain,
            "capability": capability,
            "messages": messages,
            "max_tokens": max_tokens,
        })

        text = "\n".join(
            str(message.get("content", ""))
            for message in messages
            if isinstance(message, dict)
        ).lower()

        # First CodingOrgan model call: classify the requested coding task.
        # CodingOrgan sends its classification instructions in the user
        # message, not through the optional system argument.
        if (
            '"kind": "code_change"' in text
            and '"kind": "clarify"' in text
            and '"kind": "other"' in text
        ):
            return (
                '{"kind":"code_change",'
                '"files":["coding_v1_probe.py"],'
                '"summary":"Create answer() returning 42"}'
            )

        # Second CodingOrgan model call: produce the complete file write.
        return (
            '{"writes":[{"path":"coding_v1_probe.py",'
            '"content":"def answer():\\n    return 42\\n"}]}'
        )


class NullMemory:
    """Minimal governed-memory boundary for this execution test."""

    def recall_tested(self, *args, **kwargs):
        return []

    def recall_rejections(self, *args, **kwargs):
        return []

    def propose_knowledge(self, *args, **kwargs):
        return {
            "status": "proposed",
            "proposal_id": "coding-v1-test-proposal",
        }


class CodingV1VerticalTests(unittest.TestCase):

    def setUp(self):
        self.project_root = Path(__file__).resolve().parents[1]
        # ToolBroker's workspace_root is also the trusted project/security
        # root used by ResourceClassifier. Therefore the real Inventory and
        # Broker must share the actual project root.
        self.workspace = self.project_root
        self.probe = self.project_root / "coding_v1_probe.py"

        if self.probe.exists():
            self.probe.unlink()

        self.inventory = Inventory(self.project_root).discover()

        guard = GuardLayer(
            self.project_root,
            policy=build_production_guard_policy(),
            effect_policy=build_production_effect_policy(),
        )

        principal = GuardPrincipal(
            principal_id="trainer.coding-v1-vertical",
            kind="human",
            role="trainer",
            authenticated=True,
            source="auth_service",
        )

        self.broker = ToolBroker(
            workspace_root=self.workspace,
            tools_dir=self.project_root / "section_8_tools",
            guard=guard,
            principal=principal,
            inventory=self.inventory,
        )

        info = self.inventory.get("coder")
        self.assertIsNotNone(info)
        self.assertEqual(info.entry_module, "coding.coding_engine")

        # Production bootstrap exposes section boundaries as import roots.
        # Reproduce that runtime contract here without changing production.
        # Reproduce the production bootstrap's section-boundary import
        # environment. Components intentionally import through their section
        # roots (for example coding.coding_engine -> mind.organ).
        central_mind_root = self.project_root / "section_1_central_mind"
        memory_root = self.project_root / "section_3_memory"
        domains_root = self.project_root / "section_5_domains"
        models_root = self.project_root / "section_7_models"
        tools_root = self.project_root / "section_8_tools"

        for import_root in (
            central_mind_root,
            memory_root,
            domains_root,
            models_root,
            tools_root,
        ):
            value = str(import_root)
            if value not in sys.path:
                sys.path.insert(0, value)

        module = __import__(
            info.entry_module,
            fromlist=[info.entry_attr],
        )
        self.organ = getattr(module, info.entry_attr)

    def tearDown(self):
        if self.probe.exists():
            self.probe.unlink()

        pycache = self.project_root / "__pycache__"
        if pycache.exists():
            for candidate in pycache.glob("coding_v1_probe.*.pyc"):
                candidate.unlink()

    def test_real_coder_write_compile_verify_appraise_cycle(self):
        caller = DeterministicCoderCaller()

        request = {
            "text": (
                "Create coding_v1_probe.py with a function answer() "
                "that returns 42."
            ),
            "caller": caller,
            "broker": self.broker.bind_component(
                self.inventory.get("coder")
            ),
            "memory": NullMemory(),
            "cognitive_plan": {
                "selected_component": "coder",
                "selected_capability": "write_code",
            },
        }

        response = self.organ.handle(request)

        self.assertIsInstance(response, dict)
        self.assertEqual(
            response.get("status"),
            "ok",
            response,
        )

        target = self.probe

        self.assertTrue(
            target.exists(),
            f"Coder did not create {target}",
        )

        namespace = {}
        exec(target.read_text(), namespace)

        self.assertEqual(namespace["answer"](), 42)

        verification = Verifier().verify(
            response,
            self.organ,
        )

        self.assertTrue(
            verification.get("ok"),
            verification,
        )

        appraisal = SelfAppraiser().appraise(
            objective=request["text"],
            response=response,
            verification=verification,
            component="coder",
            domain="Cod",
            provider="deterministic-coder-test",
        )

        self.assertEqual(
            appraisal.objective_outcome,
            "success",
        )
        self.assertEqual(
            appraisal.verification_state,
            "passed",
        )

        history = list(self.broker.history)

        operations = [
            row.get("tool")
            or row.get("operation")
            or row.get("name")
            for row in history
            if isinstance(row, dict)
        ]

        self.assertGreaterEqual(
            len(caller.calls),
            2,
            "Coder did not perform both model stages.",
        )

        # The response itself is the authoritative CodingOrgan evidence.
        verification_evidence = response.get("verification") or {}
        checks = verification_evidence.get("checks") or {}

        self.assertTrue(
            checks.get("file_writes"),
            response,
        )
        self.assertEqual(
            checks.get("python_syntax"),
            "passed",
            response,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
