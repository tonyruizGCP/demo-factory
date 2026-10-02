"""Chapter 3: Frequentist A/B Testing & Power Analysis.

Implements:
- Power Analysis Calculator:
  * `calculate_required_sample_size(p1, p2, alpha=0.05, power=0.80)` for unpaired two-sample
    proportions and paired McNemar discordant proportions.
- Synthetic Paired Experiment Generator:
  * Simulates baseline vs. candidate agent runs on identical tasks with shared task difficulty
    (producing a 2x2 contingency table of paired binary outcomes + skewed token/latency data).
- Statistical Tests:
  * McNemar's Test with Edwards' continuity correction (`(|b - c| - 1)^2 / (b + c)`).
  * Wilcoxon Signed-Rank Test for paired skewed continuous metrics (token usage / latency).
  * Independent 2-sample Z-test for proportions.
- Monte Carlo Sample-Efficiency Comparison (1,000 trials):
  * Demonstrates why McNemar's paired test achieves 80%+ power with 5x-10x fewer samples
    than an unlinked 2-sample Z-test when task-level correlation is high.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats


def calculate_required_sample_size(
    p1: float,
    p2: float,
    alpha: float = 0.05,
    power: float = 0.80,
    paired_correlation: Optional[float] = None,
) -> int:
    """Calculate required sample size N (tasks) for binary pass/fail agent evaluations.

    If `paired_correlation` is None, computes standard two-sample independent proportion
    sample size per arm using normal approximation with pooled/unpooled variance:
        N_unpaired = ((z_{1-alpha/2}*sqrt(2*p_bar*(1-p_bar)) + z_{power}*sqrt(p1*(1-p1)+p2*(1-p2)))^2) / (p2 - p1)^2

    If `paired_correlation` (phi correlation in [0, 1)) is provided, computes the paired
    McNemar sample size accounting for shared task difficulty correlation:
        p_discordant = p1*(1-p1) + p2*(1-p2) - 2*rho*sqrt(p1*(1-p1)*p2*(1-p2))
    """
    if abs(p2 - p1) < 1e-9:
        raise ValueError("p1 and p2 must differ to compute sample size.")

    z_alpha = float(stats.norm.ppf(1.0 - alpha / 2.0))
    z_beta = float(stats.norm.ppf(power))
    delta = abs(p2 - p1)

    if paired_correlation is None:
        p_bar = 0.5 * (p1 + p2)
        term1 = z_alpha * np.sqrt(2.0 * p_bar * (1.0 - p_bar))
        term2 = z_beta * np.sqrt(p1 * (1.0 - p1) + p2 * (1.0 - p2))
        n_req = ((term1 + term2) ** 2) / (delta**2)
        return int(np.ceil(n_req))

    # Paired McNemar sample size formula (Connor 1987)
    sd1 = np.sqrt(p1 * (1.0 - p1))
    sd2 = np.sqrt(p2 * (1.0 - p2))
    cov = paired_correlation * sd1 * sd2
    p12 = np.clip(p1 * (1.0 - p2) - cov, 1e-5, 0.99)  # Baseline Pass, Candidate Fail (b)
    p21 = np.clip(p2 * (1.0 - p1) - cov, 1e-5, 0.99)  # Baseline Fail, Candidate Pass (c)
    psi = p12 + p21  # Total discordant proportion
    n_paired = (
        (z_alpha * np.sqrt(psi) + z_beta * np.sqrt(psi - (p21 - p12) ** 2)) ** 2
    ) / ((p21 - p12) ** 2)
    return int(np.ceil(n_paired))


@dataclass
class PairedExperimentData:
    """Container for a paired A/B benchmark run on N tasks."""

    baseline_pass: np.ndarray  # shape (N,), 0/1
    candidate_pass: np.ndarray  # shape (N,), 0/1
    baseline_tokens: np.ndarray  # shape (N,), skewed continuous
    candidate_tokens: np.ndarray  # shape (N,), skewed continuous
    contingency_table: np.ndarray  # 2x2 [[a (1,1), b (1,0)], [c (0,1), d (0,0)]]


def simulate_paired_experiment(
    num_tasks: int = 120,
    p_baseline: float = 0.65,
    p_candidate: float = 0.70,
    discordant_noise: float = 0.012,
    random_state: int = 42,
) -> PairedExperimentData:
    """Simulate paired baseline vs. candidate agent runs on identical tasks.

    Because both agents run on the EXACT SAME benchmark tasks, task difficulty
    strongly couples their outcomes: a task that baseline passes is very likely
    passed by candidate (except for small regression rate `b = discordant_noise`),
    while candidate solves `c = (p_candidate - p_baseline) + discordant_noise` of
    baseline's failures.
    """
    rng = np.random.default_rng(random_state)
    delta = p_candidate - p_baseline
    prob_b = max(0.002, discordant_noise)  # Baseline Pass (1), Candidate Fail (0)
    prob_c = max(0.002, delta + prob_b)    # Baseline Fail (0), Candidate Pass (1)
    prob_a = max(0.01, p_baseline - prob_b)  # Both Pass (1, 1)
    prob_d = max(0.01, 1.0 - (prob_a + prob_b + prob_c))  # Both Fail (0, 0)
    probs = np.array([prob_a, prob_b, prob_c, prob_d])
    probs = probs / probs.sum()

    outcomes = rng.choice([0, 1, 2, 3], size=num_tasks, p=probs)
    baseline_pass = np.isin(outcomes, [0, 1]).astype(int)
    candidate_pass = np.isin(outcomes, [0, 2]).astype(int)

    a = int(np.sum((baseline_pass == 1) & (candidate_pass == 1)))
    b = int(np.sum((baseline_pass == 1) & (candidate_pass == 0)))
    c = int(np.sum((baseline_pass == 0) & (candidate_pass == 1)))
    d = int(np.sum((baseline_pass == 0) & (candidate_pass == 0)))
    table = np.array([[a, b], [c, d]])

    # Simulate skewed continuous token usage (log-normal coupled by task length)
    task_base_log_tokens = rng.normal(loc=7.6, scale=0.65, size=num_tasks)
    baseline_tokens = np.exp(task_base_log_tokens + rng.normal(0.0, 0.18, size=num_tasks))
    # Candidate uses ~14% fewer tokens on average with skewed tail
    candidate_tokens = np.exp(
        task_base_log_tokens - 0.15 + rng.normal(0.0, 0.18, size=num_tasks)
    )

    return PairedExperimentData(
        baseline_pass=baseline_pass,
        candidate_pass=candidate_pass,
        baseline_tokens=baseline_tokens,
        candidate_tokens=candidate_tokens,
        contingency_table=table,
    )


def mcnemar_test(
    baseline_pass: np.ndarray,
    candidate_pass: np.ndarray,
    continuity_correction: bool = True,
) -> Dict[str, float]:
    """Perform McNemar's test on paired binary outcomes.

    Contingency cells:
        b = count(baseline == 1 and candidate == 0)
        c = count(baseline == 0 and candidate == 1)
    With continuity correction (Edwards, 1948):
        chi2 = (|b - c| - 1)^2 / (b + c)
    """
    b = int(np.sum((baseline_pass == 1) & (candidate_pass == 0)))
    c = int(np.sum((baseline_pass == 0) & (candidate_pass == 1)))
    discordant = b + c
    if discordant == 0:
        return {"b": b, "c": c, "statistic": 0.0, "p_value": 1.0}

    if continuity_correction:
        num = max(0.0, abs(b - c) - 1.0) ** 2
    else:
        num = float((b - c) ** 2)
    chi2_stat = num / float(discordant)
    p_val = float(stats.chi2.sf(chi2_stat, df=1))
    return {"b": b, "c": c, "statistic": float(chi2_stat), "p_value": p_val}


def independent_two_sample_z_test(
    baseline_pass: np.ndarray, candidate_pass: np.ndarray
) -> Dict[str, float]:
    """Perform an unpaired 2-sample Z-test for proportions (ignoring task pairing)."""
    n1 = len(baseline_pass)
    n2 = len(candidate_pass)
    p1 = float(np.mean(baseline_pass))
    p2 = float(np.mean(candidate_pass))
    p_pool = (np.sum(baseline_pass) + np.sum(candidate_pass)) / float(n1 + n2)
    denom = np.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n1 + 1.0 / n2))
    if denom < 1e-12:
        return {"z_stat": 0.0, "p_value": 1.0, "p1": p1, "p2": p2}
    z_stat = (p2 - p1) / denom
    p_val = float(2.0 * stats.norm.sf(abs(z_stat)))
    return {"z_stat": float(z_stat), "p_value": p_val, "p1": p1, "p2": p2}


def wilcoxon_signed_rank_test(
    baseline_metric: np.ndarray, candidate_metric: np.ndarray
) -> Dict[str, float]:
    """Perform Wilcoxon Signed-Rank test on paired skewed continuous metrics."""
    res = stats.wilcoxon(candidate_metric, baseline_metric, alternative="two-sided")
    return {
        "statistic": float(res.statistic),
        "p_value": float(res.pvalue),
        "median_baseline": float(np.median(baseline_metric)),
        "median_candidate": float(np.median(candidate_metric)),
        "median_diff": float(np.median(candidate_metric - baseline_metric)),
    }


def run_monte_carlo_power_comparison(
    sample_sizes: List[int],
    p_baseline: float = 0.65,
    p_candidate: float = 0.70,
    discordant_noise: float = 0.008,
    num_trials: int = 1000,
    alpha: float = 0.05,
    random_state: int = 42,
) -> pd.DataFrame:
    """Run 1,000 Monte Carlo trials per sample size comparing McNemar vs Unpaired Z-test."""
    rng = np.random.default_rng(random_state)
    delta = p_candidate - p_baseline
    prob_b = discordant_noise
    prob_c = delta + prob_b
    prob_a = p_baseline - prob_b
    prob_d = 1.0 - (prob_a + prob_b + prob_c)
    probs = np.array([prob_a, prob_b, prob_c, prob_d])

    records = []
    for n in sample_sizes:
        # Vectorized multinomial simulation across `num_trials`
        counts = rng.multinomial(n, probs, size=num_trials)
        a = counts[:, 0]
        b = counts[:, 1]
        c = counts[:, 2]

        # McNemar with continuity correction
        disc = b + c
        mcnemar_stat = np.where(
            disc > 0, (np.maximum(0.0, np.abs(b - c) - 1.0) ** 2) / np.maximum(1, disc), 0.0
        )
        mcnemar_p = stats.chi2.sf(mcnemar_stat, df=1)
        mcnemar_power = float(np.mean(mcnemar_p < alpha))

        # Independent 2-sample Z-test
        s1 = a + b
        s2 = a + c
        p1_hat = s1 / float(n)
        p2_hat = s2 / float(n)
        p_pool = (s1 + s2) / float(2 * n)
        se = np.sqrt(np.maximum(1e-12, p_pool * (1.0 - p_pool) * (2.0 / n)))
        z_stat = np.abs(p2_hat - p1_hat) / se
        z_p = 2.0 * stats.norm.sf(z_stat)
        unpaired_power = float(np.mean(z_p < alpha))

        records.append(
            {
                "sample_size": n,
                "mcnemar_paired_power": mcnemar_power,
                "unpaired_z_power": unpaired_power,
            }
        )
    return pd.DataFrame(records)
