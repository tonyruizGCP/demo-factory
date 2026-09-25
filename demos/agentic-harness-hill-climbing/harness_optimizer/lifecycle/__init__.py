"""Lifecycle & Holdout Verification Module.

Exports:
- HoldoutGate: McNemar paired holdout testing with continuity correction and exact binomial fallback
- HoldoutDecision: Immutable evaluation result
- mcnemar_test: Paired hypothesis test helper
- OptimizationStateMachine: 7-state lifecycle finite state machine
- OptimizationState: The 7 lifecycle states
- InvalidStateTransitionError: Transition guard error
- LifecycleStateMachine: Alias for OptimizationStateMachine
- LifecycleState: Alias for OptimizationState
- StateTransitionError: Alias for InvalidStateTransitionError
- HillClimbingOrchestrator: High-level lifecycle orchestrator
"""

from .holdout_gate import (
    HoldoutDecision,
    HoldoutGate,
    mcnemar_test,
)
from .orchestrator import HillClimbingOrchestrator
from .state_machine import (
    InvalidStateTransitionError,
    LifecycleState,
    LifecycleStateMachine,
    OptimizationState,
    OptimizationStateMachine,
    StateTransitionError,
)

__all__ = [
    "HoldoutDecision",
    "HoldoutGate",
    "mcnemar_test",
    "OptimizationState",
    "LifecycleState",
    "OptimizationStateMachine",
    "LifecycleStateMachine",
    "InvalidStateTransitionError",
    "StateTransitionError",
    "HillClimbingOrchestrator",
]
