"""Chapter 5: Bayesian Sequential Testing & Early Stopping.

Implements:
- Closed-form Beta-Binomial conjugate posterior updating: Beta(alpha + s, beta + n - s)
- Posterior Probability of Superiority P(theta_cand > theta_base | D):
  1. Monte Carlo sampling (`numpy`)
  2. Exact numerical quadrature (`scipy.integrate.quad` + `scipy.stats.beta`)
- `BetaBinomialEvaluator`: sequential decision engine with configurable boundaries:
  * Early Accept (P >= 0.95)
  * Early Abandon (P <= 0.10)
  * `step(candidate_pass, baseline_pass)` -> returns "ACCEPT", "ABANDON", or "CONTINUE"
- Compute-Savings Benchmark:
  * Simulates evaluating 100 weak prompt variants and 10 strong prompt variants against
    a baseline, comparing fixed N=500 sweeps vs. Bayesian sequential early stopping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Tuple
import numpy as np
import pandas as pd
from scipy import integrate, special, stats


DecisionStatus = Literal["ACCEPT", "ABANDON", "CONTINUE"]


def update_beta_posterior(
    alpha_prior: float, beta_prior: float, successes: int, trials: int
) -> Tuple[float, float]:
    """Closed-form conjugate Beta-Binomial update: Beta(alpha + s, beta + n - s)."""
    return float(alpha_prior + successes), float(beta_prior + (trials - successes))


def prob_superiority_monte_carlo(
    alpha_cand: float,
    beta_cand: float,
    alpha_base: float,
    beta_base: float,
    num_samples: int = 50_000,
    rng: np.random.Generator | None = None,
) -> float:
    """Estimate P(theta_cand > theta_base | D) via Monte Carlo Beta sampling."""
    if rng is None:
        rng = np.random.default_rng(42)
    samples_cand = rng.beta(alpha_cand, beta_cand, size=num_samples)
    samples_base = rng.beta(alpha_base, beta_base, size=num_samples)
    return float(np.mean(samples_cand > samples_base))


def prob_superiority_quadrature(
    alpha_cand: float,
    beta_cand: float,
    alpha_base: float,
    beta_base: float,
) -> float:
    """Compute exact P(theta_cand > theta_base | D) via 1D numerical quadrature.

    Integrates:
        int_0^1 PDF_cand(x) * CDF_base(x) dx
    using `scipy.integrate.quad` and `scipy.stats.beta`.
    """
    dist_cand = stats.beta(alpha_cand, beta_cand)
    dist_base = stats.beta(alpha_base, beta_base)

    def integrand(x: float) -> float:
        return float(dist_cand.pdf(x) * dist_base.cdf(x))

    val, _ = integrate.quad(integrand, 0.0, 1.0, limit=100)
    return float(np.clip(val, 0.0, 1.0))


@dataclass
class BetaBinomialEvaluator:
    """Sequential Bayesian A/B evaluator with early Accept / Abandon stopping boundaries."""

    alpha_prior: float = 1.0
    beta_prior: float = 1.0
    accept_threshold: float = 0.95
    abandon_threshold: float = 0.10
    min_trials_before_stopping: int = 15
    max_trials: int = 500
    use_quadrature: bool = False
    random_state: int = 42

    alpha_cand: float = field(init=False)
    beta_cand: float = field(init=False)
    alpha_base: float = field(init=False)
    beta_base: float = field(init=False)
    trials_run: int = field(init=False, default=0)
    cand_successes: int = field(init=False, default=0)
    base_successes: int = field(init=False, default=0)
    history: List[Dict[str, object]] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self.rng = np.random.default_rng(self.random_state)
        self.reset()

    def reset(self) -> None:
        """Reset posterior parameters to the initial Beta(alpha_prior, beta_prior)."""
        self.alpha_cand = float(self.alpha_prior)
        self.beta_cand = float(self.beta_prior)
        self.alpha_base = float(self.alpha_prior)
        self.beta_base = float(self.beta_prior)
        self.trials_run = 0
        self.cand_successes = 0
        self.base_successes = 0
        self.history = []

    def current_prob_superiority(self, mc_samples: int = 15_000) -> float:
        """Compute current posterior probability P(theta_candidate > theta_baseline | D)."""
        if self.use_quadrature:
            return prob_superiority_quadrature(
                self.alpha_cand, self.beta_cand, self.alpha_base, self.beta_base
            )
        return prob_superiority_monte_carlo(
            self.alpha_cand,
            self.beta_cand,
            self.alpha_base,
            self.beta_base,
            num_samples=mc_samples,
            rng=self.rng,
        )

    def step(
        self, candidate_pass: int | bool, baseline_pass: int | bool
    ) -> DecisionStatus:
        """Observe one paired (or sequential) task outcome and return stopping decision."""
        c_hit = int(bool(candidate_pass))
        b_hit = int(bool(baseline_pass))

        self.trials_run += 1
        self.cand_successes += c_hit
        self.base_successes += b_hit

        self.alpha_cand, self.beta_cand = update_beta_posterior(
            self.alpha_prior, self.beta_prior, self.cand_successes, self.trials_run
        )
        self.alpha_base, self.beta_base = update_beta_posterior(
            self.alpha_prior, self.beta_prior, self.base_successes, self.trials_run
        )

        p_sup = self.current_prob_superiority()
        status: DecisionStatus = "CONTINUE"
        if self.trials_run >= self.min_trials_before_stopping:
            if p_sup >= self.accept_threshold:
                status = "ACCEPT"
            elif p_sup <= self.abandon_threshold:
                status = "ABANDON"

        self.history.append(
            {
                "trial": self.trials_run,
                "alpha_cand": self.alpha_cand,
                "beta_cand": self.beta_cand,
                "alpha_base": self.alpha_base,
                "beta_base": self.beta_base,
                "prob_superiority": p_sup,
                "decision": status,
            }
        )
        return status


def run_compute_savings_benchmark(
    num_weak_variants: int = 100,
    num_strong_variants: int = 10,
    max_trials_per_variant: int = 500,
    p_baseline: float = 0.65,
    accept_threshold: float = 0.95,
    abandon_threshold: float = 0.10,
    min_trials: int = 20,
    check_interval: int = 5,
    random_state: int = 42,
) -> Dict[str, object]:
    """Simulate evaluating 100 weak variants and 10 strong variants against a baseline.

    Compares Fixed-Horizon (N=500 per variant) vs. Bayesian Sequential Early Stopping.
    Uses vectorized normal approximation of Beta posterior difference during intermediate
    batch steps and exact Beta Monte Carlo verification at boundaries for fast, exact execution.
    """
    rng = np.random.default_rng(random_state)
    total_variants = num_weak_variants + num_strong_variants
    fixed_total_trials = total_variants * max_trials_per_variant

    variant_records = []
    for idx in range(total_variants):
        is_strong = idx >= num_weak_variants
        if is_strong:
            # Strong prompt variants improve baseline by +6% to +11%
            p_cand = float(rng.uniform(p_baseline + 0.06, p_baseline + 0.11))
            v_type = "Strong Variant"
        else:
            # Weak prompt variants are worse or slightly inferior (-12% to -1%)
            p_cand = float(rng.uniform(p_baseline - 0.12, p_baseline - 0.01))
            v_type = "Weak Variant"

        # Pre-sample up to max_trials_per_variant
        cand_outcomes = (rng.random(max_trials_per_variant) < p_cand).astype(int)
        base_outcomes = (rng.random(max_trials_per_variant) < p_baseline).astype(int)

        decision = "CONTINUE"
        stopped_at = max_trials_per_variant
        final_p_sup = 0.5

        for n in range(min_trials, max_trials_per_variant + 1, check_interval):
            s_c = int(cand_outcomes[:n].sum())
            s_b = int(base_outcomes[:n].sum())
            a_c, b_c = 1.0 + s_c, 1.0 + (n - s_c)
            a_b, b_b = 1.0 + s_b, 1.0 + (n - s_b)

            p_sup = prob_superiority_monte_carlo(
                a_c, b_c, a_b, b_b, num_samples=6000, rng=rng
            )
            final_p_sup = p_sup
            if p_sup >= accept_threshold:
                decision = "ACCEPT"
                stopped_at = n
                break
            if p_sup <= abandon_threshold:
                decision = "ABANDON"
                stopped_at = n
                break

        variant_records.append(
            {
                "variant_id": f"VAR-{idx + 1:03d}",
                "variant_type": v_type,
                "true_p_cand": p_cand,
                "true_p_base": p_baseline,
                "trials_used": stopped_at,
                "fixed_trials": max_trials_per_variant,
                "decision": decision,
                "final_prob_superiority": final_p_sup,
            }
        )

    df_variants = pd.DataFrame(variant_records)
    sequential_total_trials = int(df_variants["trials_used"].sum())
    compute_savings_pct = (
        1.0 - (sequential_total_trials / float(fixed_total_trials))
    ) * 100.0

    return {
        "variants_df": df_variants,
        "fixed_total_trials": fixed_total_trials,
        "sequential_total_trials": sequential_total_trials,
        "trials_saved": fixed_total_trials - sequential_total_trials,
        "compute_savings_pct": compute_savings_pct,
        "weak_avg_trials": float(
            df_variants[df_variants["variant_type"] == "Weak Variant"][
                "trials_used"
            ].mean()
        ),
        "strong_avg_trials": float(
            df_variants[df_variants["variant_type"] == "Strong Variant"][
                "trials_used"
            ].mean()
        ),
    }
