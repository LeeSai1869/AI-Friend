"""Deterministic audit stage for gated proposals."""
from __future__ import annotations
from typing import Any, Dict, List


DEFAULT_POLICY = {
    "self_directed": {
        "allowed_risk_levels": {"low", "medium"},
        "required_evidence_keys": {"reason", "observed_signal"},
        "dependents_scan_required": True,
        "affects_central_mind_acknowledgement_required": True,
    },
    "removal": {
        "allowed_risk_levels": {"low", "medium", "high"},
        "required_evidence_keys": {"reason", "failure_evidence"},
        "dependents_scan_required": True,
        "affects_central_mind_acknowledgement_required": True,
    },
    "feature_expansion": {
        "allowed_risk_levels": {"low", "medium"},
        "required_evidence_keys": {
            "reason",
            "observed_signal",
            "package_validation",
            "tests_passed",
            "protected_scope_check",
            "targets",
        },
        "dependents_scan_required": True,
        "affects_central_mind_acknowledgement_required": True,
    },
}


class AuditStage:
    def __init__(self, policy=None):
        self.policy = dict(policy) if isinstance(policy, dict) else dict(DEFAULT_POLICY)

    def evaluate(self, proposal) -> Dict[str, Any]:
        kind = getattr(proposal, "kind", None)
        policy = self.policy.get(kind)
        if policy is None:
            return self._v("fail", f"no audit policy for {kind!r}", [])
        checked = []
        risk = str((getattr(proposal, "risk", {}) or {}).get("level", "")).lower()
        if risk not in policy["allowed_risk_levels"]:
            return self._v("fail", f"risk {risk!r} not allowed", ["risk_level"])
        checked.append("risk_level")
        ev = dict(getattr(proposal, "evidence", {}) or {})
        missing = [k for k in policy["required_evidence_keys"]
                   if k not in ev or ev[k] is None or ev[k] == ""]
        if missing:
            return self._v("needs_more_evidence",
                           f"missing: {sorted(missing)!r}", checked + ["required_evidence"])
        checked.append("required_evidence")
        if kind == "feature_expansion" and (
            getattr(proposal, "affects_central_mind", False)
            or ev.get("protected_scope_check") is not True
            or ev.get("tests_passed") is not True
            or ev.get("package_validation") is not True
        ):
            return self._v(
                "fail",
                "feature expansion failed protected-scope or package validation",
                checked + ["feature_package"],
            )
        if kind == "feature_expansion":
            targets = ev.get("targets")
            if not isinstance(targets, list) or not targets:
                return self._v(
                    "needs_more_evidence",
                    "feature targets must be listed",
                    checked + ["targets"],
                )
            allowed_roots = (
                "section_5_domains/",
                "section_6_capabilities/",
                "section_8_tools/",
            )
            for target in targets:
                path = str(target or "").replace("\\", "/")
                parts = path.split("/")
                if (
                    path.startswith("/")
                    or not path.startswith(allowed_roots)
                    or any(part in {"", ".", ".."} for part in parts)
                    or path.lower().endswith(".md")
                ):
                    return self._v(
                        "fail",
                        f"protected or invalid feature target: {path!r}",
                        checked + ["targets"],
                    )
            checked.append("targets")
        if policy["dependents_scan_required"] and "dependents_scan" not in ev:
            return self._v("needs_more_evidence", "dependents_scan required",
                           checked + ["dependents_scan"])
        checked.append("dependents_scan")
        if (policy["affects_central_mind_acknowledgement_required"]
                and bool(getattr(proposal, "affects_central_mind", False))):
            if ev.get("affects_central_mind_acknowledged") is not True:
                return self._v("needs_more_evidence",
                               "affects_central_mind_acknowledged required",
                               checked + ["affects_central_mind_acknowledgement"])
            checked.append("affects_central_mind_acknowledgement")
        return self._v("pass", "all checks passed", checked)

    @staticmethod
    def _v(verdict, reason, checked):
        return {"verdict": verdict, "reason": reason, "checked": list(checked)}
