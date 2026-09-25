"""Hill-Climbing Orchestrator coordinating lifecycle execution.

Wraps the 7-state lifecycle finite state machine, Harbor batch execution,
Bayesian sequential early stopping, and McNemar paired holdout verification.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from harness_optimizer.bayesian.engine import BetaBinomialModel, posterior_superiority
from harness_optimizer.bayesian.stopping import EarlyStoppingController, StoppingDecision
from harness_optimizer.benchhub.schema import ATIFTask, BenchmarkSuite
from harness_optimizer.benchhub.splitter import StratifiedSplitter, SplitResult
from harness_optimizer.lifecycle.holdout_gate import HoldoutGate, HoldoutDecision
from harness_optimizer.lifecycle.state_machine import (
    OptimizationState,
    OptimizationStateMachine,
)


class HillClimbingOrchestrator:
    """Orchestrates closed-loop hill-climbing optimization across the lifecycle."""

    def __init__(
        self,
        state_machine: Optional[OptimizationStateMachine] = None,
        holdout_gate: Optional[HoldoutGate] = None,
        stopping_controller: Optional[EarlyStoppingController] = None,
        splitter: Optional[StratifiedSplitter] = None,
        alpha: float = 0.05,
    ):
        self.state_machine = state_machine or OptimizationStateMachine()
        self.holdout_gate = holdout_gate or HoldoutGate(alpha=alpha)
        self.stopping_controller = stopping_controller or EarlyStoppingController()
        self.splitter = splitter or StratifiedSplitter()
        self.active_baseline: Any = None
        self.history: List[Dict[str, Any]] = []

    def reset(self) -> None:
        """Resets the orchestrator and underlying state machine."""
        self.state_machine.reset()
        self.active_baseline = None
        self.history.clear()

    def evaluate_holdout(
        self,
        baseline_results: Sequence[Any],
        candidate_results: Sequence[Any],
    ) -> HoldoutDecision:
        """Evaluates paired holdout results through the HoldoutGate and updates state machine."""
        decision = self.holdout_gate.evaluate(baseline_results, candidate_results)
        self.state_machine.handle_holdout_decision(decision)
        return decision

    def evaluate_candidate_stopping(
        self,
        step: int,
        p_superiority: float,
    ) -> StoppingDecision:
        """Evaluates Bayesian stopping condition and advances state machine if conclusive."""
        decision = self.stopping_controller.evaluate(step=step, p_superiority=p_superiority)
        if decision != StoppingDecision.CONTINUE:
            self.state_machine.handle_stopping_decision(decision)
        return decision
