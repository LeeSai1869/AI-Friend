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

        raw_rows = self.memory.recall(
            query=objective,
            memory_class="raw",
            limit=self.DEFAULT_RECALL_LIMIT,
        )
        rows = self.memory.recall(
            query=objective,
            limit=self.DEFAULT_RECALL_LIMIT,
        )

        combined = []
        seen = set()
        for item in list(raw_rows or []) + list(rows or []):
            if not isinstance(item, dict):
                continue
            memory_id = item.get("id")
            if memory_id and memory_id in seen:
                continue
            if memory_id:
                seen.add(memory_id)
            combined.append(item)

        selected = [dict(item) for item in combined[:self.DEFAULT_RECALL_LIMIT]]
        # Budget recalled source text explicitly instead of silently overflowing
        # the semantic provider's context as memories grow.
        per_record = 24000 // max(1, len(selected))
        for item in selected:
            content = item.get("content")
            if isinstance(content, str) and len(content) > per_record:
                item.setdefault("content_chars", len(content))
                item["content"] = content[:per_record]
                item["content_truncated"] = True
                item["context_limit_reason"] = "Mind recall text budget: 24000 characters shared across selected records"
        return selected

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
                if str(row.get("kind") or "").strip().lower() != "domain":
                    # Tools are used by domains through the Broker; they are not plan steps.
                    continue

                normalized = dict(row)
                normalized["purpose"] = "execution"
                info = self.inventory.get(str(row.get("component") or ""))
                manifest = getattr(info, "manifest", {}) or {}
                normalized["acceptance_check_contracts"] = dict(manifest.get("acceptance_check_contracts", {}))
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
        checks = proposal.get("acceptance_checks", [])
        state.acceptance_checks = list(checks) if isinstance(checks, list) else []
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

    def _note_drop(self, step_id, component, capability, reason) -> None:
        """Remember why a proposed step was not accepted, for diagnosis and re-planning."""
        rows = getattr(self, "last_dropped_steps", None)
        if rows is None:
            rows = []
            self.last_dropped_steps = rows
        rows.append({
            "step_id": str(step_id or ""),
            "component": str(component or ""),
            "capability": str(capability or ""),
            "reason": reason,
        })

    def _validate_steps(
        self,
        rows: List[Dict[str, Any]],
        objective: str,
        *,
        evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Validate final execution proposals against trusted Inventory."""

        valid: List[Dict[str, Any]] = []
        known_ids = set()
        consulted_evidence = {
            (
                str(item.get("source") or "").strip(),
                str((item.get("metadata") or {}).get("capability") or "").strip(),
            )
            for item in (evidence or [])
            if isinstance(item, dict)
            and isinstance(item.get("metadata"), dict)
        }
        evidence_step_ids = set()
        for index, row in enumerate(rows or []):
            if not isinstance(row, dict) or row.get("kind", "domain") != "domain":
                continue

            component = str(row.get("component") or "").strip()
            capability = str(row.get("capability") or "").strip()
            info = getattr(
                self.inventory,
                "get",
                lambda _name: None,
            )(component) if self.inventory is not None else None
            manifest = getattr(info, "manifest", {}) or {}
            declarations = (
                manifest.get("evidence_capabilities", {})
                if isinstance(manifest, dict)
                else {}
            )
            if (
                isinstance(declarations, dict)
                and capability in declarations
                and (component, capability) in consulted_evidence
            ):
                evidence_step_ids.add(str(
                    row.get("step_id") or f"step_{index + 1}"
                ).strip())

        for index, row in enumerate(rows or []):
            if not isinstance(row, dict):
                continue

            step_id = str(
                row.get("step_id")
                or f"step_{index + 1}"
            ).strip()

            if not step_id or step_id in known_ids:
                self._note_drop(step_id, row.get("component"), row.get("capability"), "duplicate or empty step identity")
                continue
            if step_id in evidence_step_ids:
                # Ambient evidence already fulfilled this read-only request.
                continue

            kind = str(
                row.get("kind")
                or "domain"
            ).strip().lower()

            if kind not in {"domain", "communicate"}:
                self._note_drop(step_id, row.get("component"), row.get("capability"), "unknown step kind")
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
                    self._note_drop(step_id, component, capability,
                                    "the step names no component or capability")
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
                    self._note_drop(step_id, component, capability,
                                    "the component and capability pair is not in the trusted catalog")
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
                    self._note_drop(step_id, component, capability,
                                    "the component is not a domain; tools and models are used by domains and are not planned as steps")
                    continue

            dependencies = self._strings(
                row.get("depends_on")
            )
            dependencies = [
                dependency
                for dependency in dependencies
                if dependency not in evidence_step_ids
            ]

            # Dependencies may only point backward to already accepted steps.
            if any(
                dependency not in known_ids
                for dependency in dependencies
            ):
                self._note_drop(step_id, component, capability, "dependency does not identify an accepted prior step")
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

    def _gather_ambient_evidence(self, state: ReasoningState) -> None:
        """Gather evidence that domains declare as ambient.

        A domain marks a read-only evidence capability ``ambient`` when it is
        cheap and relevant to every turn (for example live project state).
        Central Mind does not interpret the evidence; it only ensures the
        understanding step never has to guess at it.
        """
        if not self.consultation.available():
            return

        proposals = []
        for row in self._semantic_catalog():
            metadata = row.get("metadata")
            if (
                row.get("purpose") == "evidence"
                and isinstance(metadata, dict)
                and metadata.get("read_only") is True
                and metadata.get("ambient") is True
            ):
                proposals.append({
                    "component": row["component"],
                    "capability": row["capability"],
                    "subject": row["capability"],
                    "question": (
                        "Provide your current read-only ambient evidence for "
                        "this turn. Do not execute the requested task. "
                        "Objective: " + state.objective[:1000]
                    ),
                    "rationale": ["the domain declares this evidence as ambient"],
                })

        partition = self.discovery.trusted_consultations(
            proposals,
            already_consulted=[],
        )

        for item in partition.get("trusted", []):
            result = self.consultation.request(
                component=item["component"],
                capability=item["capability"],
                subject=item.get("subject", ""),
                question=item["question"],
                reasoning_state=state.as_dict(),
                context=state.supplied_context,
            )
            state.investigation_results.append(dict(result))
            if not result.get("ok"):
                continue
            state.add_evidence(
                source_kind="domain",
                source=item["component"],
                subject=item.get("subject") or item["capability"],
                value=result.get("evidence"),
                confidence=1.0,
                metadata={
                    "capability": item["capability"],
                    "read_only_consultation": True,
                    "ambient": True,
                },
            )

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

        proposed = [item for item in proposed if isinstance(item, dict)]

        def without_previous_results(items):
            previous = {
                (
                    str(result.get("component") or "").strip().casefold(),
                    str(result.get("capability") or "").strip().casefold(),
                    str(result.get("subject") or "").strip().casefold(),
                )
                for result in state.investigation_results
                if isinstance(result, dict)
            }
            return [
                item
                for item in items
                if (
                    str(item.get("component") or "").strip().casefold(),
                    str(item.get("capability") or "").strip().casefold(),
                    str(item.get("subject") or "").strip().casefold(),
                ) not in previous
            ]

        partition = self.discovery.trusted_consultations(
            without_previous_results(proposed),
            already_consulted=state.consulted_components,
        )

        if not partition.get("trusted") and state.missing_information:
            unresolved = ", ".join(state.missing_information[:8])
            objective = state.objective[:2000]
            evidence_capabilities = [
                row
                for row in self._semantic_catalog()
                if row.get("purpose") == "evidence"
                and isinstance(row.get("metadata"), dict)
                and row["metadata"].get("read_only") is True
                and not any(
                    item.get("source") == row["component"]
                    and (item.get("metadata") or {}).get("capability") == row["capability"]
                    for item in state.evidence_payload()
                )
            ][:state.max_consultations]
            fallback = [
                {
                    "component": row["component"],
                    "capability": row["capability"],
                    # The capability supplies facts about itself. Merely
                    # calling it must not claim an unrelated human need was resolved.
                    "subject": row["capability"],
                    "question": (
                        "For the user's objective, provide any relevant "
                        "trusted evidence this declared read-only capability "
                        "can supply. Do not execute the requested task. "
                        f"Objective: {objective}. "
                        f"Unresolved information: {unresolved}."
                    ),
                    "rationale": [
                        "A material information need remains unresolved and "
                        "the model did not propose a trusted consultation."
                    ],
                }
                for row in evidence_capabilities
            ]
            fallback_partition = self.discovery.trusted_consultations(
                without_previous_results(fallback),
                already_consulted=state.consulted_components,
            )
            partition["trusted"].extend(fallback_partition["trusted"])
            partition["rejected"].extend(fallback_partition["rejected"])

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

        evidence = state.evidence_payload()
        evidence_subjects = {
            " ".join(str(item.get("subject") or "").split()).casefold():
                str(item.get("subject") or "").strip()
            for item in evidence
            if isinstance(item, dict) and str(item.get("subject") or "").strip()
        }
        normalized_needs = []
        for item in needs:
            if not isinstance(item, dict):
                continue
            need = dict(item)
            subject = " ".join(
                str(need.get("subject") or "").split()
            ).casefold()
            if subject in evidence_subjects:
                need["subject"] = evidence_subjects[subject]
            normalized_needs.append(need)

        unresolved = self.discovery.unresolved_material_needs(
            normalized_needs,
            evidence,
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

        asked_attributes = {
            str(item.get("attribute") or "").strip()
            for item in questions
        }
        for item in unresolved:
            subject = str(item.get("subject") or "").strip()
            if subject and subject not in asked_attributes:
                questions.append({
                    "attribute": subject,
                    "question": (
                        f"I don't have enough trusted information about "
                        f"{subject}. Could you clarify it?"
                    ),
                    "options": [],
                    "default": None,
                })

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
        self.last_evidence = state.evidence_payload()
        steps = []

        validated = self._validate_steps(
            state.candidate_steps,
            state.objective,
            evidence=state.evidence_payload(),
        )
        for row in validated:
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
            acceptance_checks=list(state.acceptance_checks),
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

        self.last_dropped_steps = []

        state = ReasoningState(
            objective=text,
            supplied_context=supplied_context,
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

        try:
            state.recalled_memory = self._recall(text)
        except Exception as exc:
            state.reasoning_error = (
                f"Central Mind memory recall failed: {exc}"
            )
            state.rationale.append(
                "reasoning stopped because shared Memory could not be checked"
            )
            return self._to_plan(state)
        state.memory_ids = self._memory_ids(state.recalled_memory)

        self._gather_ambient_evidence(state)

        prior: Optional[Dict[str, Any]] = None
        replanned = False

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

            drops_before = len(getattr(self, "last_dropped_steps", None) or [])
            validated = self._validate_steps(
                state.candidate_steps,
                state.objective,
                evidence=state.evidence_payload(),
            )
            new_drops = list(getattr(self, "last_dropped_steps", None) or [])[drops_before:]

            if validated and not new_drops:
                state.candidate_steps = validated
                state.missing_information = []
                state.clarification_questions = []
                break

            if new_drops and not replanned:
                # Steps were proposed but none passed validation. Tell the
                # understanding resource why and ask once more before treating
                # the request as plain communication.
                replanned = True
                feedback = [
                    "step %s (%s / %s): %s" % (
                        d["step_id"], d["component"] or "-", d["capability"] or "-", d["reason"],
                    )
                    for d in new_drops
                ]
                retry = self._semantic_proposal(
                    state,
                    prior={**proposal, "validation_feedback": feedback},
                )
                if not str(retry.get("error") or "").strip():
                    retry_drops_before = len(self.last_dropped_steps)
                    revalidated = self._validate_steps(
                        retry.get("candidate_steps") or [],
                        state.objective,
                        evidence=state.evidence_payload(),
                    )
                    if revalidated and len(self.last_dropped_steps) == retry_drops_before:
                        self._assimilate_proposal(state, retry)
                        state.candidate_steps = revalidated
                        state.missing_information = []
                        state.clarification_questions = []
                        break

            if new_drops:
                state.reasoning_error = "The plan contains invalid action steps after one repair attempt; no action was executed."
                state.candidate_steps = []
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
