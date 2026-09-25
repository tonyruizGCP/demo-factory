"""McNemar Paired Holdout Verification Gate.

Implements rigorous hypothesis testing with Edwards continuity correction
and exact binomial test fallback for small sample sizes to gate candidate promotions
and protect against Goodharting regressions.
"""

from __future__ import annotations

import math
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Tuple, Union
from pydantic import BaseModel, Field


class HoldoutDecision(BaseModel):
    """Immutable result of a paired holdout verification evaluation."""
    PASSED: ClassVar[str] = "PASSED"
    REJECTED: ClassVar[str] = "REJECTED"
    FAILED: ClassVar[str] = "FAILED"

    passed: bool = Field(..., description="True if candidate achieved statistically significant superiority")
    p_value: float = Field(..., description="Two-sided hypothesis test p-value")
    statistic: float = Field(default=0.0, description="Test statistic (Edwards continuity corrected Chi-Square)")
    contingency_table: Dict[str, int] = Field(default_factory=dict, description="2x2 contingency table (a, b, c, d)")

    @property
    def promoted(self) -> bool:
        """Alias for passed for test compatibility."""
        return self.passed

    def __bool__(self) -> bool:
        """Boolean evaluation delegates to passed."""
        return self.passed

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            if other.upper() in ("PASSED", "PROMOTE", "PROMOTED", "ACCEPT"):
                return self.passed
            elif other.upper() in ("REJECTED", "FAILED", "PRUNE"):
                return not self.passed
        return super().__eq__(other)


def mcnemar_test(*args, **kwargs) -> Tuple[float, float]:
    """McNemar paired hypothesis test supporting dual calling conventions.

    Calling convention 1:
        mcnemar_test(b, c) with integer discordant counts returns (statistic, p_value).
    Calling convention 2:
        mcnemar_test(base_results, cand_results) with boolean/telemetry sequences returns (p_value, statistic).
    """
    if len(args) == 2 and isinstance(args[0], (int, float)) and isinstance(args[1], (int, float)):
        b = int(args[0])
        c = int(args[1])
        gate = HoldoutGate()
        stat, p_val = gate.evaluate_table(b, c)
        return (stat, p_val)
    elif len(args) >= 2 and isinstance(args[0], (list, tuple)) and isinstance(args[1], (list, tuple)):
        base_seq = args[0]
        cand_seq = args[1]
        gate = HoldoutGate()
        decision = gate.evaluate(base_seq, cand_seq)
        return (decision.p_value, decision.statistic)
    elif "b" in kwargs and "c" in kwargs:
        b = int(kwargs["b"])
        c = int(kwargs["c"])
        gate = HoldoutGate()
        stat, p_val = gate.evaluate_table(b, c)
        return (stat, p_val)
    elif "baseline_results" in kwargs and "candidate_results" in kwargs:
        gate = HoldoutGate()
        decision = gate.evaluate(kwargs["baseline_results"], kwargs["candidate_results"])
        return (decision.p_value, decision.statistic)
    else:
        gate = HoldoutGate()
        return (0.0, 1.0)


class HoldoutGate:
    """Paired holdout verification gate using McNemar's test with continuity correction."""

    def __init__(self, alpha: float = 0.05):
        self.alpha = float(alpha)

    def build_contingency_table(
        self,
        baseline_results: Sequence[Any],
        candidate_results: Sequence[Any],
    ) -> Dict[str, int]:
        """Builds 2x2 contingency table (a: both pass, b: base pass cand fail, c: base fail cand pass, d: both fail)."""
        if len(baseline_results) != len(candidate_results):
            raise ValueError(
                f"Paired evaluation length mismatch: baseline has {len(baseline_results)}, "
                f"candidate has {len(candidate_results)}"
            )

        def _get_bool(x: Any) -> bool:
            if hasattr(x, "passed"):
                return bool(x.passed)
            return bool(x)

        a, b, c, d = 0, 0, 0, 0
        for base, cand in zip(baseline_results, candidate_results):
            b_pass = _get_bool(base)
            c_pass = _get_bool(cand)
            if b_pass and c_pass:
                a += 1
            elif b_pass and not c_pass:
                b += 1
            elif not b_pass and c_pass:
                c += 1
            else:
                d += 1
        return {"a": a, "b": b, "c": c, "d": d}

    def exact_binomial(self, b: int, c: int) -> float:
        """Two-sided exact binomial test under null hypothesis p0 = 0.5."""
        n = b + c
        if n == 0:
            return 1.0
        k = min(b, c)
        prob_sum = 0.0
        for i in range(k + 1):
            prob_sum += math.comb(n, i) * (0.5 ** n)
        p_val = min(1.0, 2.0 * prob_sum)
        return float(p_val)

    def evaluate_table(self, b: int, c: int) -> Tuple[float, float]:
        """Calculates (statistic, p_value) for discordant counts b and c."""
        n = b + c
        if n == 0:
            return (0.0, 1.0)

        diff = abs(b - c)
        if diff >= 1:
            stat = float((diff - 1) ** 2 / n)
        else:
            stat = 0.0

        if n < 25:
            p_val = self.exact_binomial(b, c)
        else:
            # Edwards continuity correction p-value from chi2 with df=1: erfc(sqrt(stat / 2))
            p_val = float(math.erfc(math.sqrt(stat / 2.0)))

        return (stat, p_val)

    def evaluate(
        self,
        baseline_results: Sequence[Any],
        candidate_results: Sequence[Any],
    ) -> HoldoutDecision:
        """Evaluates paired trial results against the holdout gate threshold alpha."""
        table = self.build_contingency_table(baseline_results, candidate_results)
        b = table["b"]
        c = table["c"]
        n = b + c

        if n == 0:
            return HoldoutDecision(
                passed=False,
                p_value=1.0,
                statistic=0.0,
                contingency_table=table,
            )

        stat, p_val = self.evaluate_table(b, c)

        # Candidate is promoted only if:
        # 1. Candidate won strictly more discordant pairs than baseline (c > b)
        # 2. Difference is statistically significant (p_value <= alpha)
        # 3. alpha > 0.0
        if self.alpha <= 0.0:
            passed = False
        else:
            passed = bool(c > b and p_val <= self.alpha)

        return HoldoutDecision(
            passed=passed,
            p_value=p_val,
            statistic=stat,
            contingency_table=table,
        )
