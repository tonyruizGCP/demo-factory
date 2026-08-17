"""Unit tests for Strategic Model Routing and Human-in-the-Loop Safety Gates."""

from core.human_in_the_loop import HighStakesActionType, HumanInTheLoopGate
from core.model_router import ModelRouter, TaskComplexity


def test_strategic_model_router():
    router = ModelRouter()

    triage_route = router.route(TaskComplexity.FAST_TRIAGE)
    assert triage_route["model_name"] == "gemini-2.5-flash"
    assert triage_route["thinking_budget"] == 1024

    reasoning_route = router.route(TaskComplexity.DEEP_REASONING)
    assert reasoning_route["model_name"] == "gemini-3.7-flash"
    assert reasoning_route["thinking_budget"] == 2048

    synthesis_route = router.route(TaskComplexity.CRITICAL_SYNTHESIS)
    assert synthesis_route["model_name"] == "gemini-2.5-pro"
    assert synthesis_route["thinking_budget"] == 4096

    override_route = router.route(TaskComplexity.FAST_TRIAGE, requested_model="gemini-3.7-flash")
    assert override_route["model_name"] == "gemini-3.7-flash"


def test_human_in_the_loop_gate():
    gate = HumanInTheLoopGate(auto_approve_policy=False)

    # 1. High stakes action should stage as pending in non-interactive mode
    approved = gate.request_approval(
        request_id="req-001",
        action_type=HighStakesActionType.HOST_ISOLATION,
        target_resource="WORKSTATION-09",
        proposed_by_agent="Lead Threat Hunter",
        justification="C2 beacon detected to malicious IP 198.51.100.23",
        risk_level="HIGH",
    )
    assert approved is False

    pending = gate.list_pending_approvals()
    assert len(pending) == 1
    assert pending[0].request_id == "req-001"

    # 2. Operator submits manual approval
    success = gate.submit_review("req-001", approved=True, notes="Confirmed malicious beacon")
    assert success is True
    assert len(gate.list_pending_approvals()) == 0
    assert gate.approval_history[-1].approved is True


def test_human_in_the_loop_auto_approve_policy():
    auto_gate = HumanInTheLoopGate(auto_approve_policy=True)
    approved = auto_gate.request_approval(
        request_id="req-auto-01",
        action_type=HighStakesActionType.SIGMA_RULE_DEPLOY,
        target_resource="SOC-SIEM",
        proposed_by_agent="Forensic Evidence Verifier",
        justification="Deploy Sigma rule for certutil download",
    )
    assert approved is True
