"""Human-in-the-Loop (HITL) Safety Approval Hooks and Verification Gates."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field
from core.logger import get_logger

logger = get_logger("hitl_gate")


class HighStakesActionType:
    HOST_ISOLATION = "host_isolation"
    ACCOUNT_SUSPENSION = "account_suspension"
    FIREWALL_RULE_BLOCK = "firewall_rule_block"
    REMEDIATION_PATCH = "remediation_patch"
    SIGMA_RULE_DEPLOY = "sigma_rule_deploy"


class ApprovalRequest(BaseModel):
    """Encapsulates a high-stakes action awaiting human confirmation."""
    request_id: str
    action_type: str
    target_resource: str
    proposed_by_agent: str
    justification: str
    risk_level: str = Field(default="HIGH", description="LOW, MEDIUM, HIGH, CRITICAL")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    approved: Optional[bool] = None
    reviewer_notes: Optional[str] = None


class HumanInTheLoopGate:
    """Manages explicit code stops requiring human confirmation before high-stakes execution."""

    def __init__(self, auto_approve_policy: bool = False):
        self.auto_approve_policy = auto_approve_policy
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.approval_history: List[ApprovalRequest] = []
        self._interactive_callback: Optional[Callable[[ApprovalRequest], bool]] = None

    def register_interactive_callback(self, callback: Callable[[ApprovalRequest], bool]) -> None:
        """Register a terminal or UI callback function to prompt human reviewer."""
        self._interactive_callback = callback

    def request_approval(
        self,
        request_id: str,
        action_type: str,
        target_resource: str,
        proposed_by_agent: str,
        justification: str,
        risk_level: str = "HIGH",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Request human confirmation before executing a high-stakes action.

        Args:
            request_id: Unique identifier for the action request.
            action_type: Type of high-stakes action (e.g. host isolation).
            target_resource: Affected infrastructure resource (host, IP, user).
            proposed_by_agent: Name of the agent proposing the action.
            justification: Forensic reasoning why the action is required.
            risk_level: Assessed risk level.
            parameters: Action-specific payload parameters.

        Returns:
            bool: True if approved by human reviewer; False if rejected or timeout.
        """
        req = ApprovalRequest(
            request_id=request_id,
            action_type=action_type,
            target_resource=target_resource,
            proposed_by_agent=proposed_by_agent,
            justification=justification,
            risk_level=risk_level,
            parameters=parameters or {},
        )

        logger.warning(
            f"HITL Safety Stop: {proposed_by_agent} requested approval for '{action_type}' on '{target_resource}' (Risk: {risk_level})",
            extra={"action_type": action_type, "target_resource": target_resource, "risk_level": risk_level}
        )

        if self.auto_approve_policy:
            req.approved = True
            req.reviewer_notes = "Auto-approved via non-interactive safety policy"
            self.approval_history.append(req)
            return True

        if self._interactive_callback:
            try:
                approved = self._interactive_callback(req)
                req.approved = approved
                self.approval_history.append(req)
                return approved
            except Exception as e:
                logger.error(f"HITL Interactive prompt failed: {e}")
                req.approved = False
                self.approval_history.append(req)
                return False

        # In headless / test environments without active prompt, stage as pending and fail closed
        self.pending_approvals[request_id] = req
        return False

    def list_pending_approvals(self) -> List[ApprovalRequest]:
        """List all requests currently blocked awaiting human review."""
        return list(self.pending_approvals.values())

    def submit_review(self, request_id: str, approved: bool, notes: Optional[str] = None) -> bool:
        """Submit a human decision on a pending request."""
        req = self.pending_approvals.pop(request_id, None)
        if not req:
            return False
        req.approved = approved
        req.reviewer_notes = notes or ("Approved by operator" if approved else "Rejected by operator")
        self.approval_history.append(req)
        return True


# Global default HITL gate
hitl_gate = HumanInTheLoopGate(auto_approve_policy=False)
