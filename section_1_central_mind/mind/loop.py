"""Central Mind — the orchestration loop.

Seven orchestration parts, four evolution parts, one interface,
zero content. The mind reads everything and writes nothing.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .inventory import Inventory
from .router import Router
from .composer import Composer
from .questioner import Questioner
from .verifier import Verifier
from .scorer import Scorer
from .reasoner import Reasoner
from .appraiser import SelfAppraiser
from .learner import Learner
from .capability_expansion import CapabilityExpansion
class CentralMind:

    def __init__(
        self,
        project_root: Path,
        chatbox,
        guards=None,
        principal=None,
    ):
        self.project_root = Path(project_root).resolve()
        self.chatbox = chatbox
        self.guards = guards
        self.principal = principal

        # Workspace root — where the mind reads and writes.
        # This is the parent of section_1_central_mind.
        self.workspace_root = self.project_root

        # The Tool Broker. All file access goes through this.
        from .broker import ToolBroker
        budget = 20
        try:
            from config import load_config
            cfg = load_config(self.project_root)
            budget = int(cfg.get("tool_budget", 20))
        except Exception:
            pass

        self.inventory = Inventory(self.project_root).discover()

        broker_kwargs = {
            "workspace_root": self.workspace_root,
            "tools_dir": self.workspace_root / "section_8_tools",
            "budget": budget,
            "logger": self._log_tool,
            "inventory": self.inventory,
        }

        # Guard and authenticated principal are installed as one trusted
        # execution context. ToolBroker rejects partial security context.
        if guards is not None and principal is not None:
            broker_kwargs["guard"] = guards
            broker_kwargs["principal"] = principal

        self.broker = ToolBroker(**broker_kwargs)

        # The memory bridge. Imported as a package so relative imports work.
        # Keep the service attribute defined even if initialization fails.
        self.memory_service = None
        try:
            import section_3_memory
            from section_3_memory.api import Memory as _Memory
            from section_3_memory.service import MemoryService

            self.memory_store = _Memory()
            self.memory_service = MemoryService(self.memory_store)
            self.memory = self.memory_service.client(
                actor="central_mind",
                role="central_mind",
                domain="Mind",
            )
            self.memory_service.register_proposal_handler(
                self._receive_memory_proposal
            )
            print("[mind] shared memory service loaded")
        except Exception as e:
            print(f"[mind] memory bridge failed to load: {e}")
            self.memory_store = None
            self.memory = None

        from .caller import Caller
        from .proposals import ProposalQueue
        from .resource_socket import ResourceRequirement, ResourceSocket

        # LLM registry — reads section_7_models/models_registry.yaml.
        # This is the router for LLM selection inside a domain, not
        # the organ router below.
        registry_path = self.project_root / "section_7_models" / "models_registry.yaml"
        try:
            try:
                from model_router import ModelRouter
            except ImportError:
                from section_7_models.model_router import ModelRouter

            self.model_router = ModelRouter(registry_path)
            self.resource_socket = ResourceSocket()
            self.resource_socket.connect(
                "model",
                lambda **kwargs: self.model_router.fulfill(
                    call_fn=self.caller._invoke_resource,
                    **kwargs,
                ),
            )
            self.resource_socket.connect(
                "domain",
                self._fulfill_domain_requirement,
            )
            print(f"[mind] model registry loaded from {registry_path}")
        except Exception as e:
            print(f"[mind] model registry failed to load: {e}")
            self.model_router = None
            self.resource_socket = ResourceSocket()
            self.resource_socket.connect(
                "domain",
                self._fulfill_domain_requirement,
            )

        self.caller = Caller(self.inventory, self._load_organ, self.model_router)
        self.proposal_queue = ProposalQueue()
        self.router = Router(self.inventory)
        self.composer = Composer()
        self.questioner = Questioner(chatbox)
        self.verifier = Verifier()
        self.scorer = Scorer(self.project_root)

        self.reasoner = Reasoner(
            inventory=self.inventory,
            memory=self.memory,
            model_router=self.model_router,
            questioner=self.questioner,
            semantic_router=self._semantic_route_model,
            resource_socket=self.resource_socket,
            requirement_factory=ResourceRequirement,
        )
        self.appraiser = SelfAppraiser()
        self.learner = Learner(memory=self.memory)
        self.capability_expansion = CapabilityExpansion(
            inventory=self.inventory,
        )
        # Evolution
        # Bookkeeping
        self.turn_count = 0
        self.chat_log: List[Dict[str, Any]] = []

    def _fulfill_domain_requirement(
        self,
        requirement,
        request,
        cognitive_plan,
        answers=None,
    ):
        """Fulfil one trusted domain requirement through the stable socket.

        Central Mind validates component identity and capability through
        Inventory, supplies shared authorized resources, and knows nothing
        about the domain's internal engines or implementation.
        """
        component = str(
            (requirement or {}).get("domain") or ""
        ).strip()
        capability = str(
            (requirement or {}).get("capability") or ""
        ).strip()

        info = self.inventory.get(component)
        if info is None or info.kind != "domain":
            return {
                "status": "error",
                "error": f"unknown domain component: {component!r}",
            }

        request_mode = str(
            (request or {}).get("mode") or "cognitive"
        ).strip().lower()

        if request_mode == "consultation":
            manifest = getattr(info, "manifest", {}) or {}
            evidence_capabilities = (
                manifest.get("evidence_capabilities", {})
                if isinstance(manifest, dict)
                else {}
            )
            if (
                not isinstance(evidence_capabilities, dict)
                or capability not in evidence_capabilities
            ):
                return {
                    "status": "error",
                    "error": (
                        f"domain {component!r} does not declare "
                        f"evidence capability {capability!r}"
                    ),
                }
        elif capability not in info.capabilities:
            return {
                "status": "error",
                "error": (
                    f"domain {component!r} does not declare "
                    f"capability {capability!r}"
                ),
            }

        organ = self._load_organ(info)
        if organ is None:
            return {
                "status": "error",
                "error": f"domain {component!r} could not be loaded",
            }

        domain_request = {
            **dict(request or {}),
            "broker": self.broker.bind_component(info),
            "caller": self.caller,
            "cognitive_plan": dict(cognitive_plan or {}),
        }

        if answers is not None:
            domain_request["answers"] = answers

        memory_service = getattr(self, "memory_service", None)
        manifest = getattr(info, "manifest", {}) or {}
        memory_domain = (
            manifest.get("memory_domain", "Gen")
            if isinstance(manifest, dict)
            else "Gen"
        )

        if memory_service is not None:
            domain_request["memory"] = memory_service.client(
                actor=getattr(info, "name", "unknown"),
                role=getattr(info, "kind", "domain") or "domain",
                domain=memory_domain,
            )

        try:
            mode = str(
                domain_request.get("mode") or "cognitive"
            ).strip().lower()

            if mode == "cognitive":
                response = organ.handle(domain_request)
            elif mode == "application":
                application_handler = getattr(
                    organ,
                    "handle_application",
                    None,
                )
                if not callable(application_handler):
                    return {
                        "status": "error",
                        "error": (
                            f"domain {component!r} provides no "
                            "application handler"
                        ),
                    }
                response = application_handler(domain_request)
            elif mode == "consultation":
                consultation_handler = getattr(
                    organ,
                    "handle_consultation",
                    None,
                )
                if not callable(consultation_handler):
                    return {
                        "status": "error",
                        "error": (
                            f"domain {component!r} provides no "
                            "consultation handler"
                        ),
                    }
                response = consultation_handler(domain_request)
            else:
                return {
                    "status": "error",
                    "error": f"unsupported domain request mode: {mode!r}",
                }
        except Exception as exc:
            return {
                "status": "error",
                "error": f"domain {component!r} failed: {exc}",
            }

        if not isinstance(response, dict):
            return {
                "status": "error",
                "error": "Domain returned a non-mapping response.",
            }

        response.setdefault("_domain_component", component)
        response.setdefault("_memory_domain", memory_domain)
        return response

    def _receive_memory_proposal(
        self, proposal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Inspect a submitted knowledge proposal through its owning domain.

        Submission remains proposal-only.  This hook gathers evaluation
        evidence; MemoryService remains the only component that can commit
        the resulting memory entry.
        """
        received = dict(proposal)
        received["status"] = "pending"
        received["received_by"] = "central_mind"
        received["received_at"] = time.time()

        domain = received.get("domain")
        candidates = [
            info
            for info in self.inventory.all()
            if info.kind == "domain"
            and (info.manifest or {}).get("memory_domain") == domain
        ]

        if len(candidates) != 1:
            received["learning_evaluation"] = {
                "ok": False,
                "testable": False,
                "reason": (
                    "no unique domain evaluator is registered for "
                    f"memory domain {domain!r}"
                ),
                "evidence": {},
            }
            return received

        info = candidates[0]
        organ = self._load_organ(info)
        if organ is None:
            received["learning_evaluation"] = {
                "ok": False,
                "testable": False,
                "reason": f"domain evaluator {info.name!r} could not be loaded",
                "evidence": {},
            }
            return received

        evaluator = getattr(organ, "evaluate_knowledge", None)
        if not callable(evaluator):
            received["learning_evaluation"] = {
                "ok": False,
                "testable": False,
                "reason": f"domain {info.name!r} provides no knowledge evaluator",
                "evidence": {},
            }
            return received

        try:
            verdict = evaluator(dict(received))
        except Exception as exc:
            verdict = {
                "ok": False,
                "testable": False,
                "reason": f"knowledge evaluation failed: {exc}",
                "evidence": {},
            }

        if not isinstance(verdict, dict):
            verdict = {
                "ok": False,
                "testable": False,
                "reason": "knowledge evaluator returned a non-dictionary verdict",
                "evidence": {},
            }

        received["learning_evaluation"] = verdict
        received["evaluated_by"] = info.name
        return received

    def learn_memory_proposal(
        self,
        proposal_id: int,
    ) -> Dict[str, Any]:
        """Apply the canonical system-learning decision.

        Raw Memory is Trainer-provided intake, not a fallback classification
        for information the system could not verify.

        System learning therefore follows this boundary:

        - testable + passed -> Tested
        - testable + failed -> Reject
        - untestable system proposal -> Reject

        Reusable system-derived learning is proposed separately by Learner as
        Derived knowledge with provenance and evidence.
        """
        if self.memory_service is None:
            raise RuntimeError("shared memory service is unavailable")

        proposal = self.memory_service.knowledge_proposal(proposal_id)
        reviewed = self._receive_memory_proposal(proposal)
        evaluation = reviewed.get("learning_evaluation") or {}

        testable = evaluation.get("testable") is True
        passed = evaluation.get("ok") is True
        reason = evaluation.get("reason")

        if not isinstance(reason, str) or not reason.strip():
            reason = "No domain verification evidence was supplied."

        if testable and not passed:
            return self.decide_memory_proposal(
                proposal_id,
                approved=False,
                reason=f"Domain verification failed: {reason}",
            )

        if not testable:
            return self.decide_memory_proposal(
                proposal_id,
                approved=False,
                reason=(
                    "System learning cannot create Raw Memory. "
                    "Domain-specific verification was unavailable: "
                    f"{reason}"
                ),
            )

        # At this point the proposal is explicitly testable and passed.
        return self.decide_memory_proposal(
            proposal_id,
            approved=True,
            reason=f"Domain verification passed: {reason}",
            memory_class="tested",
        )


    def decide_memory_proposal(
        self,
        proposal_id: int,
        *,
        approved: bool,
        reason: str,
        memory_class: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply an explicit Central Mind decision to a knowledge proposal."""
        if self.memory_service is None:
            raise RuntimeError("shared memory service is unavailable")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("decision reason must be non-empty")

        if approved is False:
            return self.memory_service.reject_knowledge_proposal(
                proposal_id,
                decided_by="central_mind",
                decision_reason=reason,
            )
        if approved is not True:
            raise ValueError("approved must be exactly True or False")
        if memory_class is None:
            raise ValueError("memory_class is required for approval")
        if memory_class == "raw":
            raise PermissionError(
                "Central Mind system learning may not create Raw Memory; "
                "Raw is reserved for authenticated Trainer Intake"
            )

        return self.memory_service.commit_approved_proposal(
            proposal_id,
            approved_by="central_mind",
            decision_reason=reason,
            approved_class=memory_class,
        )

    def _semantic_route_model(
        self,
        *,
        system: str,
        messages: List[Dict[str, str]],
    ) -> str:
        """Request a subordinate resource through the universal socket.

        Central Mind describes the qualities required for this cognitive job.
        It does not choose a model, provider, registry roster, or implementation.
        """
        if not getattr(self, "resource_socket", None):
            raise RuntimeError("resource socket unavailable")

        source_scores = {}
        if self.memory is not None:
            try:
                source_scores = self.memory.source_scores(
                    domain="general",
                    capability="reason",
                )
            except Exception:
                source_scores = {}

        from .resource_socket import ResourceRequirement

        requirement = ResourceRequirement(
            kind="model",
            capability="reason",
            domain="general",
            traits=(
                "reasoning",
                "instruction_following",
                "reliable_json_output",
            ),
            avoid_traits=(
                "reasoning_leak",
                "overthinks",
                "slow",
            ),
            structured_output="json",
            prefer_local=True,
            latency_preference="fast",
        )

        result = self.resource_socket.request(
            requirement,
            messages=[
                {"role": "system", "content": system},
                *messages,
            ],
            source_scores=source_scores,
        )

        if result.get("ok"):
            return str(result.get("output", ""))

        raise RuntimeError(
            "no suitable subordinate resource produced "
            "a semantic proposal"
        )

    def _log_tool(self, message: str) -> None:
        """Called by the broker for every tool event."""
        print(message)

    # ---- public: process one turn ---------------------------------

    def process(
        self,
        user_input: str,
        *,
        plan=None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run one bounded Central Mind cognitive turn.

        Reasoner is the semantic gateway. It decides whether the objective
        requires clarification, communication, one domain step, or an ordered
        multi-domain plan. Models remain subordinate resources. Guard remains
        authoritative for effects.
        """

        if plan is None:
            supplied_context = (
                context
                if isinstance(context, dict)
                else {
                    "turn": self.turn_count + 1,
                    "surface": "central_mind",
                }
            )

            plan = self.reasoner.plan(
                user_input,
                route=None,
                context=supplied_context,
            )

        if getattr(
            plan,
            "reasoning_error",
            None,
        ):
            return {
                "status": "error",
                "error": plan.reasoning_error,
                "cognition": {
                    "plan": plan.as_dict(),
                    "disposition": (
                        "reasoning_error"
                    ),
                },
            }

        if plan.should_clarify:
            questions = list(
                plan.clarification_questions
                or []
            )

            if not questions:
                questions = [{
                    "attribute": "clarification",
                    "question": (
                        "I need additional information "
                        "before I can reliably continue."
                    ),
                    "options": [],
                    "default": None,
                }]

            return {
                "status": "needs_answers",
                "questions": questions,
                "cognition": {
                    "plan": plan.as_dict(),
                    "disposition": "clarify",
                },
            }

        steps = list(
            getattr(
                plan,
                "steps",
                [],
            ) or []
        )

        if not steps:
            return {
                "status": "error",
                "error": (
                    "Reasoner produced no executable "
                    "or communication step."
                ),
                "cognition": {
                    "plan": plan.as_dict(),
                },
            }

        if (
            len(steps) == 1
            and steps[0].kind == "communicate"
        ):
            return {
                "status": "communicate",
                "communication": (
                    steps[0].as_dict()
                ),
                "evidence": [],
                "cognition": {
                    "plan": plan.as_dict(),
                },
            }

        from .cognition import CognitivePlan

        step_results = {}
        all_appraisals = []
        verified_outputs = []

        for step in steps:
            if step.kind == "communicate":
                continue

            missing_dependencies = [
                dep
                for dep in step.depends_on
                if dep not in step_results
            ]

            if missing_dependencies:
                return {
                    "status": "error",
                    "error": (
                        f"Step {step.step_id!r} has "
                        "unsatisfied dependencies: "
                        + ", ".join(
                            missing_dependencies
                        )
                    ),
                    "cognition": {
                        "plan": plan.as_dict(),
                        "step_results": (
                            step_results
                        ),
                        "appraisals": (
                            all_appraisals
                        ),
                    },
                }

            evidence = []

            for dependency in step.depends_on:
                dependency_result = (
                    step_results.get(
                        dependency,
                        {},
                    )
                )

                if isinstance(
                    dependency_result,
                    dict,
                ):
                    value = (
                        dependency_result.get(
                            "output"
                        )
                    )

                    if value is not None:
                        evidence.append(
                            "Verified prior step "
                            f"{dependency}: {value}"
                        )

            step_input = step.objective

            if evidence:
                step_input += (
                    "\n\n"
                    + "\n".join(evidence)
                )

            step_plan = CognitivePlan(
                objective=step.objective,
                recalled_memory=list(
                    plan.recalled_memory
                ),
                memory_ids=list(
                    plan.memory_ids
                ),
                requirements=list(
                    step.requirements
                ),
                constraints=list(
                    step.constraints
                ),
                steps=[step],
                strategy=(
                    "execute_verified_step"
                ),
                expected_outcome=(
                    step.expected_outcome
                ),
                max_attempts=(
                    plan.max_attempts
                ),
                rationale=list(
                    step.rationale
                ),
            )

            result = (
                self._execute_single_plan(
                    step_input,
                    plan=step_plan,
                )
            )

            if not isinstance(result, dict):
                return {
                    "status": "error",
                    "error": (
                        f"Step {step.step_id!r} "
                        "returned a non-mapping result."
                    ),
                    "cognition": {
                        "plan": plan.as_dict(),
                    },
                }

            step_results[
                step.step_id
            ] = result

            cognition = result.get(
                "cognition",
                {},
            )

            if isinstance(cognition, dict):
                rows = cognition.get(
                    "appraisals",
                    [],
                )

                if isinstance(rows, list):
                    all_appraisals.extend(
                        rows
                    )

            if result.get("status") != "ok":
                result["cognition"] = {
                    "plan": plan.as_dict(),
                    "step_results": (
                        step_results
                    ),
                    "appraisals": (
                        all_appraisals
                    ),
                }
                return result

            if result.get("output") is not None:
                verified_outputs.append(
                    result.get("output")
                )

        communication_steps = [
            step
            for step in steps
            if step.kind == "communicate"
        ]

        if communication_steps:
            return {
                "status": "communicate",
                "communication": (
                    communication_steps[-1]
                    .as_dict()
                ),
                "evidence": verified_outputs,
                "cognition": {
                    "plan": plan.as_dict(),
                    "step_results": (
                        step_results
                    ),
                    "appraisals": (
                        all_appraisals
                    ),
                },
            }

        combined = self.composer.combine([
            {
                "status": "ok",
                "output": output,
            }
            for output in verified_outputs
        ])

        if combined.get("status") == "ok":
            return {
                "status": "ok",
                "output": combined.get(
                    "output",
                    "",
                ),
                "cognition": {
                    "plan": plan.as_dict(),
                    "step_results": (
                        step_results
                    ),
                    "appraisals": (
                        all_appraisals
                    ),
                },
            }

        combined["cognition"] = {
            "plan": plan.as_dict(),
            "step_results": step_results,
            "appraisals": all_appraisals,
        }

        return combined

    def _execute_single_plan(
        self,
        user_input: str,
        *,
        plan=None,
    ) -> Dict[str, Any]:
        """Run one bounded Central Mind cognitive turn.

        V1 cycle:
        input -> recall/reason -> route/act -> verify -> appraise
              -> learn/capability-gap -> communicate

        Guard remains inside Broker before tool execution.
        Verifier remains post-action correctness checking.
        """
        self.turn_count += 1
        self.broker.reset_budget()

        request = {
            "text": user_input,
            "ts": time.time(),
            "turn": self.turn_count,
            "caller": self.caller,
            "memory": getattr(self, "memory", None),
        }
        self.chat_log.append({
            "role": "user",
            "text": user_input,
            "ts": request["ts"],
        })

        # Reasoner owns semantic intent understanding.  Its proposed
        # component/capability is validated against trusted Inventory before
        # Central Mind resolves an executable component.
        # A caller may already have obtained this turn's CognitivePlan
        # from this same Reasoner. Reuse it so semantic routing and permanent
        # memory recall occur once per cognitive turn.
        if plan is None:
            plan = self.reasoner.plan(
                user_input,
                route=None,
                context={
                    "turn": self.turn_count,
                    "surface": "central_mind",
                },
            )

        # Clarification is a valid cognitive outcome, not an execution failure.
        # Do not guess, deny, or invoke a domain when material information is
        # known to be missing.
        if plan.should_clarify:
            questions = list(
                getattr(plan, "clarification_questions", []) or []
            )
            if not questions:
                questions = [{
                    "attribute": "clarification",
                    "question": (
                        "I need a little more information before I can "
                        "reliably continue. What should I use?"
                    ),
                    "options": [],
                    "default": None,
                }]

            return {
                "status": "needs_answers",
                "questions": questions,
                "cognition": {
                    "plan": plan.as_dict(),
                    "disposition": "clarify",
                },
            }

        organs = []

        executable_steps = [
            step
            for step in getattr(
                plan,
                "steps",
                [],
            ) or []
            if getattr(
                step,
                "kind",
                "",
            ) == "domain"
        ]

        selected_step = (
            executable_steps[0]
            if len(executable_steps) == 1
            else None
        )

        if (
            selected_step is not None
            and selected_step.component
        ):
            selected = self.inventory.get(
                selected_step.component
            )

            if (
                selected is not None
                and selected_step.capability
                in selected.capabilities
            ):
                organs = [selected]

        if not organs:
            appraisal = self.appraiser.capability_gap(
                objective=plan.objective,
                reason="no capable component claimed request",
                memory_ids=plan.memory_ids,
            )

            capability_proposal = (
                self.capability_expansion.propose_from_appraisal(appraisal)
            )

            self.scorer.record(
                event="capability_gap",
                objective=plan.objective,
                objective_outcome=appraisal.objective_outcome,
                verification_state=appraisal.verification_state,
                disposition=appraisal.disposition,
                failure_code=appraisal.failure_code,
                memory_ids=appraisal.memory_ids,
                capability_proposal=capability_proposal,
                ts=time.time(),
            )

            result = self._no_handler(request)
            self.chat_log.append({
                "role": "mind",
                "text": result,
                "ts": time.time(),
            })
            return {
                "status": "ok",
                "output": result,
                "cognition": {
                    "disposition": appraisal.disposition,
                    "capability_gap": True,
                },
            }

        responses: List[Dict[str, Any]] = []
        appraisals: List[Dict[str, Any]] = []
        verification_failed = False

        for organ in organs:
            from .resource_socket import ResourceRequirement

            requirement = ResourceRequirement(
                kind="domain",
                domain=organ.name,
                capability=selected_step.capability,
            )

            response = self.resource_socket.request(
                requirement,
                request=request,
                cognitive_plan=plan.as_dict(),
            )

            if response.get("status") == "needs_answers":
                answers = self.questioner.ask(
                    response.get("questions", [])
                )
                response = self.resource_socket.request(
                    requirement,
                    request=request,
                    cognitive_plan=plan.as_dict(),
                    answers=answers,
                )

            real_organ = self._load_organ(organ)
            if real_organ is None:
                response = {
                    "status": "error",
                    "error": f"domain {organ.name!r} could not be loaded",
                }
                verified = {
                    "ok": False,
                    "reason": response["error"],
                }
            else:
                verified = self.verifier.verify(response, real_organ)

            appraisal = self.appraiser.appraise(
                objective=plan.objective,
                response=response,
                verification=verified,
                memory_ids=plan.memory_ids,
                component=getattr(organ, "name", None),
                domain=memory_domain,
                provider=response.get("provider"),
            )

            # Temporary operational experience only.
            # Objective result and verification result remain independent.
            self.scorer.record(
                event="cognitive_result",
                objective=plan.objective,
                originating_component=getattr(organ, "name", None),
                domain=memory_domain,
                provider=response.get("provider"),
                objective_outcome=appraisal.objective_outcome,
                verification_state=appraisal.verification_state,
                disposition=appraisal.disposition,
                failure_code=appraisal.failure_code,
                memory_ids=appraisal.memory_ids,
                reusable=appraisal.reusable,
                ts=time.time(),
            )

            # Learner does not store events. It only forwards an explicit,
            # compact reusable knowledge candidate through Memory Service.
            learning = self.learner.learn(
                appraisal,
                response=response,
                component=getattr(organ, "name", None),
            )

            capability_proposal = (
                self.capability_expansion.propose_from_appraisal(appraisal)
            )

            appraisal_row = appraisal.as_dict()
            if learning is not None:
                appraisal_row["learning_proposal"] = learning
            if capability_proposal is not None:
                appraisal_row["capability_proposal"] = capability_proposal
            appraisals.append(appraisal_row)

            # Verification failure withholds a nominally successful output,
            # but does NOT rewrite the objective outcome into "failure".
            if (
                response.get("status", "ok") == "ok"
                and verified.get("ok") is not True
            ):
                verification_failed = True
                response = {
                    "status": "error",
                    "error": (
                        "Response verification failed; output withheld."
                    ),
                }

            responses.append(response)

        if not responses:
            appraisal = self.appraiser.capability_gap(
                objective=plan.objective,
                reason="routed components could not be loaded",
                memory_ids=plan.memory_ids,
            )
            capability_proposal = (
                self.capability_expansion.propose_from_appraisal(appraisal)
            )
            self.scorer.record(
                event="capability_gap",
                objective=plan.objective,
                objective_outcome=appraisal.objective_outcome,
                verification_state=appraisal.verification_state,
                disposition=appraisal.disposition,
                failure_code=appraisal.failure_code,
                memory_ids=appraisal.memory_ids,
                capability_proposal=capability_proposal,
                ts=time.time(),
            )

            result = self._no_handler(request)
            self.chat_log.append({
                "role": "mind",
                "text": result,
                "ts": time.time(),
            })
            return {
                "status": "ok",
                "output": result,
                "cognition": {
                    "disposition": appraisal.disposition,
                    "capability_gap": True,
                },
            }

        if verification_failed:
            combined = {
                "status": "error",
                "errors": [
                    "One or more organ responses failed verification; "
                    "combined output withheld."
                ],
                "outputs": [],
            }
        else:
            combined = self.composer.combine(responses)

        if combined.get("status") == "needs_answers":
            self.chat_log.append({
                "role": "mind",
                "text": "(awaiting user)",
                "ts": time.time(),
            })
            combined["cognition"] = {
                "plan": plan.as_dict(),
                "appraisals": appraisals,
            }
            return combined

        if combined.get("status") == "ok":
            out = combined.get("output", "")
            self.chat_log.append({
                "role": "mind",
                "text": out,
                "ts": time.time(),
            })
            return {
                "status": "ok",
                "output": out,
                "cognition": {
                    "plan": plan.as_dict(),
                    "appraisals": appraisals,
                },
            }

        out = self._format_combined(combined)
        self.chat_log.append({
            "role": "mind",
            "text": out,
            "ts": time.time(),
        })
        combined["cognition"] = {
            "plan": plan.as_dict(),
            "appraisals": appraisals,
        }
        return combined

    # ---- helpers --------------------------------------------------

    def _no_handler(self, request: Dict[str, Any]) -> str:
        return (
            "No organ claimed this request.\n"
            "I have noted it. If it repeats, I will propose a new organ."
        )

    def _format_combined(self, combined: Dict[str, Any]) -> str:
        if combined.get("status") == "error":
            return "Errors:\n" + "\n".join(combined.get("errors", []))
        return str(combined)

    def _load_organ(self, info):
        """Load the organ instance from its manifest."""
        if not info.entry_module:
            print(f"[mind] load {info.name}: no entry_module")
            return None
        try:
            mod = __import__(info.entry_module, fromlist=[info.entry_attr])
        except Exception as e:
            print(f"[mind] import failed for '{info.name}' (module='{info.entry_module}'): {e!r}")
            return None
        try:
            organ = getattr(mod, info.entry_attr)
        except AttributeError as e:
            print(f"[mind] attribute failed for '{info.name}' (attr='{info.entry_attr}'): {e!r}")
            return None
        return organ

    def inventory_summary(self) -> str:
        lines = [f"Inventory: {len(self.inventory.all())} organ(s)"]
        for o in self.inventory.all():
            lines.append(f"  [{o.kind}] {o.name}  scope={o.scope}  caps={o.capabilities}")
        return "\n".join(lines)