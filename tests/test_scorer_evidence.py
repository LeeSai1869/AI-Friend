from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from section_1_central_mind.mind.scorer import (
    EvidenceContractError,
    Scorer,
)


class _Organ:
    name = "coder"

    def __init__(self):
        self.legacy_called = False

    def score_event(self, event):
        self.legacy_called = True
        raise AssertionError("legacy organ scoring must not be called")

class ScorerEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.scorer = Scorer(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_record_keeps_structured_temporary_evidence(self):
        result = self.scorer.record(
            event={
                "event": "domain_response_verified",
                "objective": "fix example.py",
                "originating_component": "coder",
                "domain": "Cod",
                "outcome": "success",
                "verification": {
                    "ok": True,
                    "reason": "syntax passed",
                },
                "evidence": {
                    "returncode": 0,
                },
            }
        )

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(
            result["verification"]["reason"],
            "syntax passed",
        )

        records = self.scorer.read_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0]["evidence"]["returncode"],
            0,
        )

    def test_memory_is_not_written_by_scorer(self):
        self.scorer.record(
            event={
                "event": "handled",
                "outcome": "success",
            }
        )
        self.assertFalse(
            any(self.root.rglob("mem_*.json"))
        )

    def test_non_json_evidence_is_rejected_not_stringified(self):
        with self.assertRaises(EvidenceContractError):
            self.scorer.record(
                event={
                    "event": "handled",
                    "evidence": {"bad": object()},
                }
            )

    def test_old_call_shape_does_not_delegate_evidence_ownership(self):
        result = self.scorer.record(
            "coder",
            {
                "event": "legacy",
                "outcome": "success",
            },
        )
        self.assertEqual(result["event"], "legacy")

    def test_mapping_only_call_shape_is_supported(self):
        result = self.scorer.record({
            "event": "mapping_form",
            "outcome": "success",
        })
        self.assertEqual(result["event"], "mapping_form")

    def test_temporary_evidence_is_bounded(self):
        scorer = Scorer(self.root, max_events=3)

        for n in range(5):
            scorer.record(
                event={
                    "event": f"event-{n}",
                    "outcome": "success",
                }
            )

        records = scorer.read_records()
        self.assertEqual(len(records), 3)
        self.assertEqual(
            [item["event"] for item in records],
            ["event-2", "event-3", "event-4"],
        )

    def test_temporary_evidence_does_not_persist_across_instances(self):
        self.scorer.record(
            event={
                "event": "first",
                "outcome": "success",
            }
        )

        restarted = Scorer(self.root)
        self.assertEqual(restarted.read_records(), [])

    def test_no_permanent_ledger_contract_exists(self):
        self.assertFalse(hasattr(self.scorer, "ledger_path"))


if __name__ == "__main__":
    unittest.main()
