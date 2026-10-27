from types import SimpleNamespace

from section_1_central_mind.mind.audit import AuditStage
from section_1_central_mind.mind.capability_expansion import CapabilityExpansion
from section_1_central_mind.mind.feature_expansion.loop import FeatureExpansionLoop
from section_1_central_mind.mind.loop import CentralMind
from section_1_central_mind.mind.proposals import ProposalQueue
from section_1_central_mind.mind.scorer import Scorer
from section_1_central_mind.mind.self_assessment.loop import SelfAssessmentLoop
from section_1_central_mind.mind.shared.questionnaire import Questionnaire


class _Inventory:
    def all(self):
        return [SimpleNamespace(name="coder")]


def test_repeated_failures_create_audited_admin_proposal_only():
    mind = CentralMind.__new__(CentralMind)
    mind.scorer = Scorer()
    mind.proposal_queue = ProposalQueue()
    mind.audit_stage = AuditStage()
    mind.inventory = _Inventory()
    mind.self_assessment = SelfAssessmentLoop(
        scorer=mind.scorer,
        proposal_queue=mind.proposal_queue,
        audit_stage=mind.audit_stage,
        inventory=mind.inventory,
    )

    for _ in range(3):
        mind._record_experience(
            event="cognitive_result",
            originating_component="coder",
            objective_outcome="failure",
            verification_state="failed",
            failure_code="test_failure",
        )

    rows = mind.proposal_queue.list()
    assert len(rows) == 1
    proposal = rows[0]
    assert proposal["kind"] == "self_directed"
    assert proposal["status"] == "audit_passed"
    assert proposal["affects_central_mind"] is True

    approved = mind.proposal_queue.record_decision(
        proposal["proposal_id"],
        decision="approve",
        actor="admin",
        reason="Review the evidence",
    )
    assert approved["status"] == "approved"
    assert not hasattr(mind.proposal_queue, "execute")


def test_central_mind_activities_have_separate_modules():
    assert CentralMind.__module__.endswith("regular_operation.loop")
    assert SelfAssessmentLoop.__module__.endswith("self_assessment.loop")
    assert FeatureExpansionLoop.__module__.endswith("feature_expansion.loop")
    assert Questionnaire.__module__.endswith("shared.questionnaire")


def test_feature_expansion_requires_audited_package_evidence():
    queue = ProposalQueue()
    audit = AuditStage()
    expansion = CapabilityExpansion(
        inventory=_Inventory(),
        proposal_queue=queue,
        audit_stage=audit,
    )
    appraisal = SimpleNamespace(
        capability_gap="missing capability",
        objective="Handle an unsupported data format",
        evidence={"reason": "No installed domain supports the format"},
        memory_ids=[],
        failure_code="missing_capability",
    )
    proposal = expansion.propose_from_appraisal(appraisal)
    queued = queue.get(proposal["proposal_id"])
    assert queued.status == "audit_needs_evidence"

    queued.evidence.update({
        "package_validation": True,
        "tests_passed": True,
        "protected_scope_check": True,
        "targets": ["section_5_domains/example_domain/entry.py"],
    })
    verdict = audit.evaluate(queued)
    audited = queue.record_audit(queued.proposal_id, verdict=verdict)

    assert audited["status"] == "audit_passed"


def test_feature_expansion_rejects_document_or_memory_targets():
    queue = ProposalQueue()
    audit = AuditStage()
    expansion = CapabilityExpansion(
        inventory=_Inventory(),
        proposal_queue=queue,
        audit_stage=audit,
    )
    appraisal = SimpleNamespace(
        capability_gap="missing capability",
        objective="Handle an unsupported data format",
        evidence={},
        memory_ids=[],
        failure_code="missing_capability",
    )
    proposal = expansion.propose_from_appraisal(appraisal)
    queued = queue.get(proposal["proposal_id"])
    queued.evidence.update({
        "package_validation": True,
        "tests_passed": True,
        "protected_scope_check": True,
        "targets": ["section_3_memory/entries/lesson.json"],
    })
    verdict = audit.evaluate(queued)
    audited = queue.record_audit(queued.proposal_id, verdict=verdict)

    assert verdict["verdict"] == "fail"
    assert audited["status"] == "audit_failed"
