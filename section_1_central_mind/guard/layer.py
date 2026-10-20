"""The guard layer: ties all guards together.

CentralMind holds one GuardLayer. All changes go through it.
"""
from __future__ import annotations

from pathlib import Path


from .contract import GuardRequest
from .policy import GuardPolicy
from .effect_policy import EffectPolicy


class GuardLayer:
    """Universal fail-closed authorization layer."""

    def __init__(
        self,
        project_root: Path,
        policy: GuardPolicy | None = None,
        effect_policy: EffectPolicy | None = None,
    ):
        self.project_root = Path(project_root).resolve()
        self.policy = policy or GuardPolicy()
        self.effect_policy = effect_policy

        # Universal action-audit trail.
        #
        # Kept in memory for the current socket contract. Persistent
        # append-only action auditing is a separate concern and must not
        # inherit the removed legacy change-pipeline assumptions.
        self.action_audit = []

    def audit_action(self, request: GuardRequest) -> dict:
        """Audit one universal action request.

        This is the generic security socket for tools, domains, models,
        capabilities, services, memory operations, and future components.

        The request describes an attempted action. It never grants authority.

        Until an explicit policy authorizes an action, the Guard Layer
        fails closed. Unknown actions are therefore BLOCK, never PASS.
        """
        if not isinstance(request, GuardRequest):
            verdict = {
                "verdict": "BLOCK",
                "reason": "Malformed guard request.",
                "checks": [
                    {
                        "name": "request_contract",
                        "passed": False,
                    }
                ],
            }
            self.action_audit.append({
                "request": None,
                "verdict": verdict,
            })
            return verdict

        record = request.to_audit_dict()

        # Human authority exists only when the trusted authentication
        # boundary has explicitly marked the human principal authenticated.
        if (
            request.principal.kind == "human"
            and request.principal.authenticated is not True
        ):
            verdict = {
                "verdict": "BLOCK",
                "reason": "Human principal is not authenticated.",
                "checks": [
                    {
                        "name": "authenticated_principal",
                        "passed": False,
                    }
                ],
            }
            self.action_audit.append({
                "request": record,
                "verdict": verdict,
            })
            return verdict

        # Internal components are identities, not human authorities.
        # Reaching this point therefore does not grant them permission.

        capability_decision = self.policy.evaluate(
            request.principal,
            request.required_capabilities,
        )

        if not capability_decision.allowed:
            verdict = {
                "verdict": "BLOCK",
                "reason": capability_decision.reason,
                "checks": [
                    {
                        "name": "request_contract",
                        "passed": True,
                    },
                    {
                        "name": "explicit_policy",
                        "passed": False,
                    },
                ],
                "required_capabilities": sorted(
                    capability_decision.required
                ),
                "granted_capabilities": sorted(
                    capability_decision.granted
                ),
                "missing_capabilities": sorted(
                    capability_decision.missing
                ),
            }
        elif self.effect_policy is None:
            # Effect authorization is mandatory for universal Guard
            # enforcement. Missing effect policy is a fail-closed
            # configuration, never a capability-only authorization mode.
            verdict = {
                "verdict": "BLOCK",
                "reason": "Effect authorization policy is not configured.",
                "checks": [
                    {
                        "name": "request_contract",
                        "passed": True,
                    },
                    {
                        "name": "explicit_policy",
                        "passed": True,
                    },
                    {
                        "name": "effect_policy",
                        "passed": False,
                    },
                ],
                "required_capabilities": sorted(
                    capability_decision.required
                ),
                "granted_capabilities": sorted(
                    capability_decision.granted
                ),
                "missing_capabilities": [],
            }
        elif not request.effects:
            # Once effect authorization is enabled, absence of a trusted
            # effect declaration is never interpreted as permission.
            verdict = {
                "verdict": "BLOCK",
                "reason": (
                    "Effect authorization is enabled but the request "
                    "contains no classified effects."
                ),
                "checks": [
                    {
                        "name": "request_contract",
                        "passed": True,
                    },
                    {
                        "name": "explicit_policy",
                        "passed": True,
                    },
                    {
                        "name": "effect_policy",
                        "passed": False,
                    },
                ],
                "required_capabilities": sorted(
                    capability_decision.required
                ),
                "granted_capabilities": sorted(
                    capability_decision.granted
                ),
                "missing_capabilities": [],
            }
        else:
            effect_decision = self.effect_policy.evaluate(
                request.effects,
                component_chain=request.component_chain,
            )

            if effect_decision.allowed:
                verdict = {
                    "verdict": "PASS",
                    "reason": effect_decision.reason,
                    "checks": [
                        {
                            "name": "request_contract",
                            "passed": True,
                        },
                        {
                            "name": "explicit_policy",
                            "passed": True,
                        },
                        {
                            "name": "effect_policy",
                            "passed": True,
                        },
                    ],
                    "required_capabilities": sorted(
                        capability_decision.required
                    ),
                    "granted_capabilities": sorted(
                        capability_decision.granted
                    ),
                    "missing_capabilities": [],
                }
            else:
                verdict = {
                    "verdict": "BLOCK",
                    "reason": effect_decision.reason,
                    "checks": [
                        {
                            "name": "request_contract",
                            "passed": True,
                        },
                        {
                            "name": "explicit_policy",
                            "passed": True,
                        },
                        {
                            "name": "effect_policy",
                            "passed": False,
                        },
                    ],
                    "required_capabilities": sorted(
                        capability_decision.required
                    ),
                    "granted_capabilities": sorted(
                        capability_decision.granted
                    ),
                    "missing_capabilities": [],
                    "denied_effect_index": (
                        effect_decision.denied_index
                    ),
                }

        self.action_audit.append({
            "request": record,
            "verdict": verdict,
        })
        return verdict
