"""Beta-Binomial Conjugate Engine for Pass Rate Evaluation.

Provides:
- BetaBinomialModel: Bayesian conjugate Beta-Binomial distribution tracking pass rates.
- posterior_superiority: Computes P(theta_cand > theta_base | D) using a two-regime solver:
  1. Small samples (<= 1000 trials): Gauss-Legendre quadrature with regularized incomplete beta CDF.
  2. Large samples (> 1000 trials): Asymptotic normal approximation via Bayesian CLT.

Neither scipy nor scikit-learn is required; implemented strictly with pure NumPy and Python math.
"""

from __future__ import annotations

import math
from typing import Any, Optional, Tuple, Union

import numpy as np


def _betacf(a: float, b: float, x: float, max_iter: int = 200, eps: float = 1e-14) -> float:
    """Evaluates continued fraction for regularized incomplete beta function via modified Lentz's method."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        # Even step
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c

        # Odd step
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        del_h = d * c
        h *= del_h
        if abs(del_h - 1.0) < eps:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _betainc(b, a, 1.0 - x)
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    log_val = a * math.log(x) + b * math.log(1.0 - x) - lbeta
    if log_val < -700.0:
        return 0.0
    factor = math.exp(log_val) / a
    return factor * _betacf(a, b, x)


# 64-node Gauss-Legendre quadrature mapped from [-1, 1] to [0, 1]
_GL_NODES, _GL_WEIGHTS = np.polynomial.legendre.leggauss(64)
_QUAD_X = 0.5 * (_GL_NODES + 1.0)
_QUAD_W = 0.5 * _GL_WEIGHTS


def _beta_pdf_log(a: float, b: float, x: np.ndarray) -> np.ndarray:
    """Log PDF of Beta(a, b) across vector x."""
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    return (a - 1.0) * np.log(x) + (b - 1.0) * np.log(1.0 - x) - lbeta


def _p_sup_quad(ac: float, bc: float, ab: float, bb: float) -> float:
    """Computes P(theta_c > theta_b) using Gauss-Legendre quadrature."""
    if ac == ab and bc == bb:
        return 0.5
    log_pdf_c = _beta_pdf_log(ac, bc, _QUAD_X)
    pdf_c = np.exp(np.clip(log_pdf_c, -700.0, 700.0))
    cdf_b = np.array([_betainc(ab, bb, xi) for xi in _QUAD_X])
    res = float(np.sum(_QUAD_W * pdf_c * cdf_b))
    return max(0.0, min(1.0, res))


def _p_sup_normal(ac: float, bc: float, ab: float, bb: float) -> float:
    """Computes P(theta_c > theta_b) via Bayesian Central Limit Theorem normal approximation."""
    if ac == ab and bc == bb:
        return 0.5
    tot_c = ac + bc
    tot_b = ab + bb
    mc = ac / tot_c
    vc = (ac * bc) / ((tot_c ** 2) * (tot_c + 1.0))
    mb = ab / tot_b
    vb = (ab * bb) / ((tot_b ** 2) * (tot_b + 1.0))
    var_sum = vc + vb
    if var_sum <= 0.0:
        return 1.0 if mc > mb else (0.5 if mc == mb else 0.0)
    z = (mc - mb) / math.sqrt(var_sum)
    res = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return max(0.0, min(1.0, res))


def _compute_superiority(ac: float, bc: float, ab: float, bb: float) -> float:
    """Dispatches to either normal approximation or quadrature based on sample size."""
    if ac + bc > 1000.0 or ab + bb > 1000.0:
        return _p_sup_normal(ac, bc, ab, bb)
    return _p_sup_quad(ac, bc, ab, bb)


def _resolve_counts(
    self_or_none: Optional[BetaBinomialModel],
    *args: Any,
    **kwargs: Any,
) -> Tuple[float, float, float, float]:
    """Resolves parameters into (ac, bc, ab, bb) for posterior superiority calculation.

    Supports:
    - (candidate_model, baseline_model)
    - (other_model) when invoked as model.posterior_superiority(other_model)
    - (cand_succ, cand_fail, base_succ, base_fail)
    - keyword arguments: candidate_successes, candidate_failures, baseline_successes, baseline_failures
    """
    prior_a = getattr(self_or_none, "alpha", 1.0) if self_or_none is not None else kwargs.get("prior_alpha", 1.0)
    prior_b = getattr(self_or_none, "beta", 1.0) if self_or_none is not None else kwargs.get("prior_beta", 1.0)

    # Check keyword arguments first
    if any(k in kwargs for k in ("candidate_successes", "cand_successes", "candidate_failures", "cand_failures")):
        c_succ = kwargs.get("candidate_successes", kwargs.get("cand_successes", 0))
        c_fail = kwargs.get("candidate_failures", kwargs.get("cand_failures", 0))
        b_succ = kwargs.get("baseline_successes", kwargs.get("base_successes", 0))
        b_fail = kwargs.get("baseline_failures", kwargs.get("base_failures", 0))
        return (
            float(prior_a + c_succ),
            float(prior_b + c_fail),
            float(prior_a + b_succ),
            float(prior_b + b_fail),
        )

    # Check positional args
    if len(args) == 4 and all(isinstance(a, (int, float)) for a in args):
        c_succ, c_fail, b_succ, b_fail = args
        return (
            float(prior_a + c_succ),
            float(prior_b + c_fail),
            float(prior_a + b_succ),
            float(prior_b + b_fail),
        )

    if len(args) == 1 and hasattr(args[0], "alpha") and hasattr(args[0], "beta"):
        if self_or_none is None:
            raise ValueError("posterior_superiority requires both candidate and baseline models")
        return (
            float(self_or_none.alpha),
            float(self_or_none.beta),
            float(args[0].alpha),
            float(args[0].beta),
        )

    if len(args) == 2 and hasattr(args[0], "alpha") and hasattr(args[1], "alpha"):
        return (
            float(args[0].alpha),
            float(args[0].beta),
            float(args[1].alpha),
            float(args[1].beta),
        )

    raise TypeError(
        f"Cannot resolve posterior_superiority arguments: args={args!r}, kwargs={kwargs!r}"
    )


class BetaBinomialModel:
    """Conjugate Beta-Binomial pass rate model with Bayesian updating and superiority calculation."""

    def __init__(
        self,
        alpha: float = 1.0,
        beta: float = 1.0,
        prior_alpha: Optional[float] = None,
        prior_beta: Optional[float] = None,
    ) -> None:
        a = prior_alpha if prior_alpha is not None else alpha
        b = prior_beta if prior_beta is not None else beta
        self.alpha: float = float(a)
        self.beta: float = float(b)
        self.prior_alpha: float = self.alpha
        self.prior_beta: float = self.beta

    def update(self, successes: int = 0, failures: int = 0) -> BetaBinomialModel:
        """Conjugate Bayesian update with observed successes and failures. Mutates in-place and returns self."""
        self.alpha += float(successes)
        self.beta += float(failures)
        return self

    def update_from_telemetry(self, telemetry: Any) -> BetaBinomialModel:
        """Increments alpha if telemetry.passed else beta. Mutates in-place and returns self."""
        if getattr(telemetry, "passed", False):
            self.alpha += 1.0
        else:
            self.beta += 1.0
        return self

    def mean(self) -> float:
        """Expected pass rate E[theta]."""
        tot = self.alpha + self.beta
        if tot <= 0.0:
            return 0.5
        return float(self.alpha / tot)

    def variance(self) -> float:
        """Variance of pass rate Var[theta]."""
        tot = self.alpha + self.beta
        if tot <= 0.0:
            return 0.0
        return float((self.alpha * self.beta) / ((tot ** 2) * (tot + 1.0)))

    def posterior_superiority(self, *args: Any, **kwargs: Any) -> float:
        """Computes P(theta_candidate > theta_baseline | D)."""
        ac, bc, ab, bb = _resolve_counts(self, *args, **kwargs)
        return _compute_superiority(ac, bc, ab, bb)

    def __repr__(self) -> str:
        return f"BetaBinomialModel(alpha={self.alpha}, beta={self.beta})"


def posterior_superiority(*args: Any, **kwargs: Any) -> float:
    """Module-level function computing P(theta_candidate > theta_baseline | D)."""
    ac, bc, ab, bb = _resolve_counts(None, *args, **kwargs)
    return _compute_superiority(ac, bc, ab, bb)
