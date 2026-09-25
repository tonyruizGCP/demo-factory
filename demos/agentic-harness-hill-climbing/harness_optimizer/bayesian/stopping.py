"""Dynamic Bayesian Sequential Early Stopping Controller.

Provides:
- StoppingDecision: Enum for early stopping outcomes (ACCEPT, PRUNE, CONTINUE).
- EarlyStoppingController: Evaluates sequential pass rates to decide whether to
  ACCEPT, PRUNE, or CONTINUE evaluation of a candidate harness configuration.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class StoppingDecision(str, Enum):
    """Decision outcome of sequential Bayesian evaluation."""

    ACCEPT = "ACCEPT"
    PRUNE = "PRUNE"
    CONTINUE = "CONTINUE"


class EarlyStoppingController:
    """Sequential early stopping controller using Bayesian posterior superiority."""

    def __init__(
        self,
        min_evals: int = 5,
        max_evals: int = 50,
        accept_threshold: float = 0.95,
        prune_threshold: float = 0.10,
        accept_p: Optional[float] = None,
        prune_p: Optional[float] = None,
    ) -> None:
        self.min_evals: int = int(min_evals)
        self.max_evals: int = int(max_evals)
        self.accept_threshold: float = float(accept_p if accept_p is not None else accept_threshold)
        self.prune_threshold: float = float(prune_p if prune_p is not None else prune_threshold)
        self.accept_p: float = self.accept_threshold
        self.prune_p: float = self.prune_threshold

    def evaluate(self, step: int, p_superiority: float) -> StoppingDecision:
        """Evaluates whether to stop or continue at the given step.

        Parameters:
            step: Current 1-based trial / evaluation count.
            p_superiority: P(theta_candidate > theta_baseline | D).

        Returns:
            StoppingDecision: ACCEPT, PRUNE, or CONTINUE.
        """
        # Guard 1: Step non-positive or warmup phase (< min_evals)
        if step <= 0 or step < self.min_evals:
            return StoppingDecision.CONTINUE

        # Guard 2: Hard cap reached (step >= max_evals) -> Must return terminal decision
        if step >= self.max_evals:
            if p_superiority >= self.accept_threshold:
                return StoppingDecision.ACCEPT
            if p_superiority <= self.prune_threshold:
                return StoppingDecision.PRUNE
            # Intermediate value at hard cap: crisp cutoff at 0.50
            return StoppingDecision.ACCEPT if p_superiority >= 0.50 else StoppingDecision.PRUNE

        # Guard 3: Evaluation window (min_evals <= step < max_evals)
        if p_superiority >= self.accept_threshold:
            return StoppingDecision.ACCEPT
        if p_superiority <= self.prune_threshold:
            return StoppingDecision.PRUNE
        return StoppingDecision.CONTINUE

    def __repr__(self) -> str:
        return (
            f"EarlyStoppingController(min_evals={self.min_evals}, "
            f"max_evals={self.max_evals}, accept_threshold={self.accept_threshold}, "
            f"prune_threshold={self.prune_threshold})"
        )
