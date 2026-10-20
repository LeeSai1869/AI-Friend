"""Central Mind Reasoner.

Reasoner owns bounded semantic understanding, uncertainty analysis,
discoverability, evidence assimilation, reconsideration, decomposition and
the final clarification/planning decision.

Models may propose interpretations. Domains may provide evidence. Neither
owns the reasoning state or grants authority.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ..cognition import CognitivePlan, CognitiveStep
from .state import ReasoningState
from .understanding import SemanticUnderstanding
from .discovery import Discovery
from .consultation import Consultation


class Reasoner:
    DEFAULT_RECALL_LIMIT = 8
    DEFAULT_MAX_ATTEMPTS = 1
    DEFAULT_MAX_CYCLES = 4
    DEFAULT_MAX_CONSULTATIONS = 3

    def __init__(
        self,
        *,
        inventory=None,
        memory=None,
        model_router=None,
        questioner=None,
        semantic_router: Optional[Callable[..., str]] = None,
        resource_socket=None,
        requirement_factory=None,
    ):
        # Existing public dependencies are preserved.
        self.inventory = inventory
        self.memory = memory
        self.model_router = model_router
        self.questioner = questioner
        self.semantic_router = semantic_router

        self.understanding = SemanticUnderstanding(
            inventory=inventory,
            semantic_resource=semantic_router,
        )
        self.discovery = Discovery(inventory=inventory)
        self.consultation = Consultation(
            resource_socket=resource_socket,
            requirement_factory=requirement_factory,
        )

    # ------------------------------------------------------------------
    # Recall
    # ------------------------------------------------------------------

    def _recall(self, objective: str) -> List[Dict[str, Any]]:
        if self.memory is None:
            return []

        try:
            rows = self.memory.recall(
                query=objective,
                limit=self.DEFAULT_RECALL_LIMIT,
            )
        except Exception:
            return []

        return [
            dict(item)
            for item in rows
            if isinstance(item, dict)
        ]

    @staticmethod
    def _memory_ids(
        recalled: List[Dict[str, Any]],
    ) -> List[str]:
        ids: List[str] = []

        for item in recalled:
            mem_id = item.get("id")
            if (
                isinstance(mem_id, str)
                and mem_id
                and mem_id not in ids
            ):
                ids.append(mem_id)

        return ids

    # ------------------------------------------------------------------
    # Trusted semantic catalog
    # ------------------------------------------------------------------

    def _semantic_catalog(self) -> List[Dict[str, Any]]:
        """Build the Reasoner's descriptive view without changing Inventory.

        Existing Inventory remains authoritative for executable capabilities.
        Evidence capabilities are optional domain-owned manifest metadata and
        are descriptive only.
        """

        rows: List[Dict[str, Any]] = []

        if self.inventory is None:
            return rows

        catalog_fn = getattr(
            self.inventory,
            "capability_catalog",
            None,
        )

        if callable(catalog_fn):
            try:
                execution_rows = catalog_fn()
            except Exception:
                execution_rows = []

            for row in execution_rows or []:
                if not isinstance(row, dict):
                    continue

                normalized = dict(row)
                normalized["purpose"] = "execution"
                rows.append(normalized)

        all_fn = getattr(self.inventory, "all", None)
        if not callable(all_fn):
            return rows

        try:
            components = all_fn()
        except Exception:
            components = []

        for info in components or []:
            if getattr(info, "kind", None) != "domain":
                continue

            manifest = getattr(info, "manifest", {}) or {}
            if not isinstance(manifest, dict):
                continue

            declarations = manifest.get(
                "evidence_capabilities",
                {},
            )
            if not isinstance(declarations, dict):
                continue

            for capability, declaration in declarations.items():
                cap = str(capability or "").strip()
                if not cap:
                    continue

                if isinstance(declaration, str):
                    description = declaration.strip()
                    metadata = {}
                elif isinstance(declaration, dict):
                    description = str(
                        declaration.get("description") or ""
                    ).strip()
                    metadata = dict(declaration)
                else:
                    continue

                rows.append({
                    "component": getattr(info, "name", ""),
                    "kind": "domain",
                    "capability": cap,
                    "purpose": "evidence",
                    "description": (
                        description
                        or cap.replace("_", " ")
                    ),
                    "metadata": metadata,
                })

        return rows

    def _semantic_proposal(
        self,
        state: ReasoningState,
        *,
        prior: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Request a subordinate proposal using a Reasoner-owned catalog."""

        return self.understanding.propose(
            objective=state.objective,
            supplied_context=state.supplied_context,
            recalled_memory=state.recalled_memory,
            evidence=state.evidence_payload(),
            prior_understanding=prior,
            capability_catalog=self._semantic_catalog(),
        )

    # ------------------------------------------------------------------
    # Proposal assimilation and validation
    # ------------------------------------------------------------------

    @staticmethod
    def _strings(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []

        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    def _assimilate_proposal(
        self,
        state: ReasoningState,
        proposal: Dict[str, Any],
    ) -> None:
        state.objective_summary = str(
            proposal.get("objective_summary")
            or state.objective
        ).strip()

        state.requirements = self._strings(
            proposal.get("requirements")
        )
        state.constraints = self._strings(
            proposal.get("constraints")
        )
        state.ambiguities = self._strings(
            proposal.get("ambiguities")
        )

        needs = proposal.get("information_needs", [])
        if not isinstance(needs, list):
            needs = []

        state.missing_information = [
            str(item.get("subject") or "").strip()
            for item in needs
            if isinstance(item, dict)
            and bool(item.get("material", True))
            and str(item.get("subject") or "").strip()
        ]

        state.candidate_steps = [
            dict(item)
            for item in proposal.get("candidate_steps", []) or []
            if isinstance(item, dict)
        ]

        state.clarification_questions = [
            dict(item)
            for item in (
                proposal.get(
                    "clarification_candidates",
                    [],
                )
                or []
            )
            if isinstance(item, dict)
        ]

        try:
            confidence = float(
                proposal.get(
                    "understanding_confidence",
                    0.0,
                )
                or 0.0
            )
        except (TypeError, ValueError):
            confidence = 0.0

        state.understanding_confidence = max(
            0.0,
            min(1.0, confidence),
        )

        state.rationale = self._strings(
            proposal.get("rationale")
        )

    def _validate_steps(
        self,
        rows: List[Dict[str, Any]],
        objective: str,
    ) -> List[Dict[str, Any]]:
        """Validate final execution proposals against trusted Inventory."""

        valid: List[Dict[str, Any]] = []
        known_ids = set()

        for index, row in enumerate(rows or []):
            if not isinstance(row, dict):
                continue

            step_id = str(
                row.get("step_id")
                or f"step_{index + 1}"
            ).strip()

            if not step_id or step_id in known_ids:
                continue

            kind = str(
                row.get("kind")
                or "domain"
            ).strip().lower()

            if kind not in {"domain", "communicate"}:
                continue

            component = row.get("component")
            capability = row.get("capability")

            if kind == "communicate":
                component = None
                capability = None
            else:
                component = str(component or "").strip()
                capability = str(capability or "").strip()

                if not component or not capability:
                    continue

                if self.inventory is None:
                    continue

                validator = getattr(
                    self.inventory,
                    "validate_capability",
                    None,
                )
                if not callable(validator):
                    continue

                try:
                    trusted = bool(
                        validator(component, capability)
                    )
                except Exception:
                    trusted = False

                if not trusted:
                    continue

                info = getattr(
                    self.inventory,
                    "get",
                    lambda _name: None,
                )(component)

                if (
                    info is None
                    or getattr(info, "kind", None) != "domain"
                ):
                    continue

            dependencies = self._strings(
                row.get("depends_on")
            )

            # Dependencies may only point backward to already accepted steps.
            if any(
                dependency not in known_ids
                for dependency in dependencies
            ):
                continue

            valid.append({
                "step_id": step_id,
                "objective": str(
                    row.get("objective")
                    or objective
                ).strip(),
                "kind": kind,
                "component": component,
                "capability": capability,
                "depends_on": dependencies,
                "requirements": self._strings(
                    row.get("requirements")
                ),
                "constraints": self._strings(
                    row.get("constraints")
                ),
                "expected_outcome": str(
                    row.get("expected_outcome")
                    or ""
                ).strip(),
                "confidence": max(
                    0.0,
                    min(
                        1.0,
                        float(
                            row.get("confidence", 0.0)
                            or 0.0
                        ),
                    ),
                ),
                "rationale": self._strings(
                    row.get("rationale")
                ),
            })

            known_ids.add(step_id)

        return valid

    # ------------------------------------------------------------------
    # Investigation
    # ------------------------------------------------------------------

    def _investigate(
        self,
        state: ReasoningState,
        proposal: Dict[str, Any],
    ) -> bool:
        """Gather trusted evidence when a discoverable route exists.

        Returns True only when new evidence was actually added.
        """

        proposed = proposal.get("consultations", [])
        if not isinstance(proposed, list):
            proposed = []

        partition = self.discovery.trusted_consultations(
            proposed,
            already_consulted=state.consulted_components,
        )

        for rejected in partition.get("rejected", []):
            reason = str(
                rejected.get("reason")
                or "consultation rejected"
            ).strip()
            if reason:
                state.rejected_hypotheses.append(reason)

        if not self.consultation.available():
            return False

        for item in partition.get("trusted", []):
            if not state.can_consult():
                break

            result = self.consultation.request(
                component=item["component"],
                capability=item["capability"],
                subject=item.get("subject", ""),
                question=item["question"],
                reasoning_state=state.as_dict(),
                context=state.supplied_context,
            )

            state.mark_consulted(item["component"])
            state.investigation_results.append(dict(result))

            if not result.get("ok"):
                continue

            state.add_evidence(
                source_kind="domain",
                source=item["component"],
                subject=(
                    item.get("subject")
                    or item["capability"]
                ),
                value=result.get("evidence"),
                confidence=1.0,
                metadata={
                    "capability": item["capability"],
                    "read_only_consultation": True,
                },
            )
            return True

        return False

    # ------------------------------------------------------------------
    # Clarification gate
    # ------------------------------------------------------------------

    def _clarification_gate(
        self,
        state: ReasoningState,
        proposal: Dict[str, Any],
    ) -> bool:
        """Ask the human only for unresolved, material, undiscovered needs."""

        needs = proposal.get("information_needs", [])
        if not isinstance(needs, list):
            needs = []

        unresolved = self.discovery.unresolved_material_needs(
            needs,
            state.evidence_payload(),
        )

        if not unresolved:
            state.missing_information = []
            state.clarification_questions = []
            return False

        unresolved_subjects = {
            str(item.get("subject") or "").strip()
            for item in unresolved
            if isinstance(item, dict)
        }

        questions = []
        for item in (
            proposal.get(
                "clarification_candidates",
                [],
            )
            or []
        ):
            if not isinstance(item, dict):
                continue

            attribute = str(
                item.get("attribute") or ""
            ).strip()

            if attribute in unresolved_subjects:
                questions.append(dict(item))

        state.missing_information = sorted(
            subject
            for subject in unresolved_subjects
            if subject
        )
        state.clarification_questions = questions

        # Missing information alone does not authorize interruption.
        # There must also be a concrete human-answerable question.
        return bool(
            state.missing_information
            and state.clarification_questions
        )

    # ------------------------------------------------------------------
    # Final contract
    # ------------------------------------------------------------------

    def _to_plan(
        self,
        state: ReasoningState,
    ) -> CognitivePlan:
        steps = []

        for row in self._validate_steps(
            state.candidate_steps,
            state.objective,
        ):
            steps.append(
                CognitiveStep(
                    step_id=row["step_id"],
                    objective=row["objective"],
                    kind=row["kind"],
                    component=row["component"],
                    capability=row["capability"],
                    depends_on=row["depends_on"],
                    requirements=row["requirements"],
                    constraints=row["constraints"],
                    expected_outcome=row["expected_outcome"],
                    confidence=row["confidence"],
                    rationale=row["rationale"],
                )
            )

        return CognitivePlan(
            objective=state.objective,
            recalled_memory=list(state.recalled_memory),
            memory_ids=list(state.memory_ids),
            requirements=list(state.requirements),
            constraints=list(state.constraints),
            ambiguities=list(state.ambiguities),
            missing_information=list(
                state.missing_information
            ),
            clarification_questions=list(
                state.clarification_questions
            ),
            understanding_confidence=(
                state.understanding_confidence
            ),
            steps=steps,
            strategy=(
                "understand_investigate_reconsider_plan_"
                "execute_verify_appraise_learn_communicate"
            ),
            expected_outcome="satisfy the stated objective",
            max_attempts=self.DEFAULT_MAX_ATTEMPTS,
            should_clarify=state.should_clarify,
            rationale=list(state.rationale),
            reasoning_error=state.reasoning_error,
        )

    def plan(
        self,
        objective: str,
        *,
        route=None,
        context: Optional[Dict[str, Any]] = None,
    ) -> CognitivePlan:
        """Produce one bounded Central Mind-owned CognitivePlan."""

        text = str(objective or "").strip()
        supplied_context = (
            dict(context)
            if isinstance(context, dict)
            else {}
        )

        recalled = self._recall(text) if text else []

        state = ReasoningState(
            objective=text,
            supplied_context=supplied_context,
            recalled_memory=recalled,
            memory_ids=self._memory_ids(recalled),
            max_cycles=self.DEFAULT_MAX_CYCLES,
            max_consultations=self.DEFAULT_MAX_CONSULTATIONS,
        )

        if not text:
            state.missing_information = ["objective"]
            state.clarification_questions = [{
                "attribute": "objective",
                "question": "What would you like me to do?",
                "options": [],
                "default": None,
            }]
            state.should_clarify = True
            state.rationale.append("the objective is empty")
            return self._to_plan(state)

        prior: Optional[Dict[str, Any]] = None

        while state.can_continue():
            state.begin_cycle()

            proposal = self._semantic_proposal(
                state,
                prior=prior,
            )

            error = str(
                proposal.get("error") or ""
            ).strip()

            if error:
                state.reasoning_error = error
                state.rationale.append(
                    "semantic reasoning failed explicitly; "
                    "no route was fabricated"
                )
                break

            self._assimilate_proposal(state, proposal)

            before_evidence = len(state.evidence)

            discovered = self._investigate(
                state,
                proposal,
            )

            if discovered:
                state.no_progress_count = 0
                prior = dict(proposal)
                continue

            if len(state.evidence) == before_evidence:
                state.no_progress_count += 1

            state.should_clarify = self._clarification_gate(
                state,
                proposal,
            )

            if state.should_clarify:
                break

            validated = self._validate_steps(
                state.candidate_steps,
                state.objective,
            )

            if validated:
                state.candidate_steps = validated
                state.missing_information = []
                state.clarification_questions = []
                break

            # A pure communication result is legitimate when understanding
            # produced no executable domain work and no unresolved material
            # human question remains.
            if not state.missing_information:
                state.candidate_steps = [{
                    "step_id": "step_1",
                    "objective": state.objective,
                    "kind": "communicate",
                    "component": None,
                    "capability": None,
                    "depends_on": [],
                    "requirements": [],
                    "constraints": [],
                    "expected_outcome": (
                        "communicate the answer to the human"
                    ),
                    "confidence": (
                        state.understanding_confidence
                    ),
                    "rationale": [
                        "no domain execution is required"
                    ],
                }]
                break

            # Do not spin when nothing new can be discovered.
            if state.no_progress_count >= 1:
                state.reasoning_error = (
                    "material information remains unresolved, "
                    "but no trusted investigation or human "
                    "clarification route was established"
                )
                break

            prior = dict(proposal)

        if (
            state.cycle_count >= state.max_cycles
            and not state.should_clarify
            and not state.candidate_steps
            and state.reasoning_error is None
        ):
            state.reasoning_error = (
                "reasoning cycle budget exhausted without "
                "a validated plan"
            )

        return self._to_plan(state)
