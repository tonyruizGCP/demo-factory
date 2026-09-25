"""Lifecycle State Machine for Hill-Climbing Optimization.

Enforces valid lifecycle state transitions across the 7-state hill-climbing lifecycle,
safeguards against regressions and Goodharting, and manages failure diagnosis routing.
"""

from __future__ import annotations

from enum import Enum
import threading
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union


class OptimizationState(str, Enum):
    """The 7 states of the hill-climbing lifecycle finite state machine."""
    IDLE = "IDLE"
    BASELINE_RUN = "BASELINE_RUN"
    CANDIDATE_SEARCH = "CANDIDATE_SEARCH"
    SEQUENTIAL_EXEC = "SEQUENTIAL_EXEC"
    HOLDOUT_GATE = "HOLDOUT_GATE"
    BASELINE_UPDATE = "BASELINE_UPDATE"
    TRACE_DIAGNOSIS = "TRACE_DIAGNOSIS"


LifecycleState = OptimizationState


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal transition is attempted in the lifecycle state machine."""
    pass


StateTransitionError = InvalidStateTransitionError


ALLOWED_TRANSITIONS: Dict[OptimizationState, Set[OptimizationState]] = {
    OptimizationState.IDLE: {
        OptimizationState.BASELINE_RUN,
        OptimizationState.IDLE,
    },
    OptimizationState.BASELINE_RUN: {
        OptimizationState.CANDIDATE_SEARCH,
        OptimizationState.BASELINE_RUN,
    },
    OptimizationState.CANDIDATE_SEARCH: {
        OptimizationState.SEQUENTIAL_EXEC,
        OptimizationState.CANDIDATE_SEARCH,
    },
    OptimizationState.SEQUENTIAL_EXEC: {
        OptimizationState.HOLDOUT_GATE,
        OptimizationState.TRACE_DIAGNOSIS,
        OptimizationState.SEQUENTIAL_EXEC,
    },
    OptimizationState.HOLDOUT_GATE: {
        OptimizationState.BASELINE_UPDATE,
        OptimizationState.TRACE_DIAGNOSIS,
        OptimizationState.HOLDOUT_GATE,
    },
    OptimizationState.BASELINE_UPDATE: {
        OptimizationState.CANDIDATE_SEARCH,
        OptimizationState.IDLE,
        OptimizationState.BASELINE_UPDATE,
    },
    OptimizationState.TRACE_DIAGNOSIS: {
        OptimizationState.CANDIDATE_SEARCH,
        OptimizationState.IDLE,
        OptimizationState.TRACE_DIAGNOSIS,
    },
}


class OptimizationStateMachine:
    """Thread-safe 7-state lifecycle finite state machine for hill-climbing optimization."""

    def __init__(self, initial_state: OptimizationState = OptimizationState.IDLE):
        self._lock = threading.RLock()
        self.current_state = initial_state
        self.state_history: List[Tuple[OptimizationState, OptimizationState]] = []
        self.active_baseline: Any = "baseline_v0"
        self.current_candidate: Any = None

    def transition(self, to_state: Union[OptimizationState, str]) -> OptimizationState:
        """Transitions to the target state if permitted by the transition matrix."""
        if isinstance(to_state, str):
            to_state = OptimizationState(to_state)

        with self._lock:
            allowed = ALLOWED_TRANSITIONS.get(self.current_state, set())
            if to_state not in allowed:
                raise InvalidStateTransitionError(
                    f"Illegal transition from {self.current_state.value} to {to_state.value}"
                )

            old_state = self.current_state
            self.current_state = to_state
            self.state_history.append((old_state, to_state))

            if to_state == OptimizationState.BASELINE_UPDATE:
                if self.current_candidate is not None:
                    self.active_baseline = self.current_candidate
                elif self.active_baseline is None:
                    self.active_baseline = "promoted_baseline"

            return self.current_state

    transition_to = transition

    def reset(self) -> None:
        """Resets the state machine back to IDLE unconditionally from any state."""
        with self._lock:
            old_state = self.current_state
            self.current_state = OptimizationState.IDLE
            self.current_candidate = None
            self.state_history.append((old_state, OptimizationState.IDLE))

    def handle_holdout_decision(self, decision: Any) -> OptimizationState:
        """Handles HoldoutDecision to branch to BASELINE_UPDATE (pass) or TRACE_DIAGNOSIS (fail)."""
        with self._lock:
            if self.current_state != OptimizationState.HOLDOUT_GATE:
                raise InvalidStateTransitionError(
                    f"Cannot handle holdout decision from state {self.current_state.value} "
                    f"(must be in HOLDOUT_GATE)"
                )
            passed = getattr(decision, "passed", getattr(decision, "promoted", bool(decision)))
            if passed:
                return self.transition(OptimizationState.BASELINE_UPDATE)
            else:
                return self.transition(OptimizationState.TRACE_DIAGNOSIS)

    def handle_stopping_decision(self, decision: Any) -> OptimizationState:
        """Handles Bayesian StoppingDecision to branch to HOLDOUT_GATE (accept) or TRACE_DIAGNOSIS (prune)."""
        with self._lock:
            if self.current_state != OptimizationState.SEQUENTIAL_EXEC:
                raise InvalidStateTransitionError(
                    f"Cannot handle stopping decision from state {self.current_state.value} "
                    f"(must be in SEQUENTIAL_EXEC)"
                )
            decision_val = getattr(decision, "value", str(decision)).upper()
            if "ACCEPT" in decision_val:
                return self.transition(OptimizationState.HOLDOUT_GATE)
            elif "PRUNE" in decision_val:
                return self.transition(OptimizationState.TRACE_DIAGNOSIS)
            elif "CONTINUE" in decision_val:
                return self.current_state
            else:
                raise ValueError(f"Unrecognized stopping decision: {decision}")

    def diagnose_failures(self, failed_telemetry: Sequence[Any]) -> Any:
        """Clusters failed trial traces using ArchetypeClusterer when in TRACE_DIAGNOSIS."""
        from harness_optimizer.clustering.archetypes import ArchetypeClusterer
        k = max(1, min(3, len(failed_telemetry)))
        clusterer = ArchetypeClusterer(k_clusters=k)
        return clusterer.cluster_telemetry(list(failed_telemetry))


LifecycleStateMachine = OptimizationStateMachine
