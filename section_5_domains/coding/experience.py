"""Bounded Coding-owned attestations for observations sent to Memory Service.

These attest only what the guarded run observed. Syntax success is never
evidence that the requested program is functionally correct.
"""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
from .tester import Tester


class CodingExperience:
    LIMIT = 128

    def __init__(self):
        self._observations = OrderedDict()

    @staticmethod
    def _key(candidate):
        fields = {key: candidate.get(key) for key in ("domain", "kind", "title", "content")}
        # Mind can append supporting memory IDs and component provenance.
        # Bind model identity while permitting those extra provenance fields.
        source = candidate.get("source") or {}
        fields["source"] = {key: source.get(key) for key in ("type", "name", "capability", "organ")}
        return hashlib.sha256(json.dumps(fields, sort_keys=True, default=str).encode()).hexdigest()

    def remember(self, candidate, assessment, functional_result=None):
        tested = functional_result is not None and Tester.passed(functional_result)
        self._observations[self._key(candidate)] = {
            "assessment": dict(assessment),
            "functional_correctness_established": tested,
            "functional_correctness_scope": "selected behavioral tests only" if tested else "not established",
            "verification_scope": (
                "observed file writes, syntax checks and the selected behavioral test suite"
                if tested else "observed file writes and Python syntax checks"
            ),
            "functional_tests": functional_result,
        }
        while len(self._observations) > self.LIMIT:
            self._observations.popitem(last=False)

    def evaluate(self, proposal):
        evidence = self._observations.get(self._key(proposal))
        if evidence is None:
            return {"ok": False, "testable": False,
                    "reason": "no matching Coding-owned run evidence; independent evaluation is required",
                    "evidence": {}}
        return {
            "ok": True, "testable": True,
            "reason": "observation matches a Coding-owned run; correctness is limited to its recorded checks",
            "evidence": dict(evidence),
        }
