"""Chapter 6: Hierarchical Bayesian Modeling for Edge Cases (Partial Pooling & Shrinkage).

Implements:
- Synthetic Low-Data Problem Setup across 8 task categories with sample sizes N_j in [3, 150],
  explicitly including sparse edge cases:
  * `distributed_race_condition` (N=3, S=0)
  * `memory_leak` (N=4, S=1)
- Three Estimators:
  1. No Pooling: Raw empirical pass rate (S_j / N_j) + Wilson/Jeffreys intervals
  2. Complete Pooling: Global average across all tasks (sum(S_j) / sum(N_j))
  3. Partial Pooling (Hierarchical Beta-Binomial Model): Estimates population hyperprior
     Beta(alpha_0, beta_0) via Empirical Bayes marginal likelihood maximization (and posterior
     shrinkage weight B_j = kappa / (kappa + N_j)), pulling small-sample edge cases toward
     the global hyperprior mean while letting high-N categories speak for themselves.
"""

from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from scipy import optimize, special, stats


def get_sparse_category_dataset() -> pd.DataFrame:
    """Create the 8-category agent evaluation dataset with uneven sample sizes (3 to 150)."""
    data = [
        {
            "category": "distributed_race_condition",
            "N": 3,
            "S": 0,
            "true_latent_rate": 0.58,
            "tier": "Sparse Edge Case (N=3)",
        },
        {
            "category": "memory_leak",
            "N": 4,
            "S": 1,
            "true_latent_rate": 0.60,
            "tier": "Sparse Edge Case (N=4)",
        },
        {
            "category": "tls_cert_rotation",
            "N": 7,
            "S": 6,
            "true_latent_rate": 0.68,
            "tier": "Low-N Slice (N=7)",
        },
        {
            "category": "schema_migration",
            "N": 18,
            "S": 11,
            "true_latent_rate": 0.64,
            "tier": "Moderate Slice (N=18)",
        },
        {
            "category": "sql_query_optimization",
            "N": 45,
            "S": 31,
            "true_latent_rate": 0.69,
            "tier": "Core Capability (N=45)",
        },
        {
            "category": "oauth_token_refresh",
            "N": 65,
            "S": 43,
            "true_latent_rate": 0.66,
            "tier": "Core Capability (N=65)",
        },
        {
            "category": "api_pagination_handling",
            "N": 110,
            "S": 82,
            "true_latent_rate": 0.74,
            "tier": "High-Volume Slice (N=110)",
        },
        {
            "category": "crud_endpoint_scaffolding",
            "N": 150,
            "S": 114,
            "true_latent_rate": 0.76,
            "tier": "High-Volume Slice (N=150)",
        },
    ]
    return pd.DataFrame(data)


def fit_hierarchical_beta_binomial(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Compute No-Pooling, Complete-Pooling, and Hierarchical Partial-Pooling estimates.

    Hierarchical Model:
        theta_j ~ Beta(alpha_0, beta_0)
        S_j | theta_j ~ Binomial(N_j, theta_j)
    We estimate (alpha_0, beta_0) by maximizing the marginal Beta-Binomial log-likelihood
    across the J categories (with a weakly informative Gamma prior on concentration
    kappa = alpha_0 + beta_0 to prevent degenerate boundary collapse).
    """
    out = df.copy()
    n_arr = out["N"].to_numpy(dtype=float)
    s_arr = out["S"].to_numpy(dtype=float)

    # 1. No Pooling (Raw MLE S_j / N_j) + Jeffreys 95% intervals for raw comparison
    out["no_pooling_mean"] = s_arr / n_arr
    raw_ci_low = []
    raw_ci_high = []
    for s, n in zip(s_arr, n_arr):
        # Clopper-Pearson / Jeffreys interval for raw binomial proportion
        lo = 0.0 if s == 0 else float(stats.beta.ppf(0.025, s + 0.5, n - s + 0.5))
        hi = 1.0 if s == n else float(stats.beta.ppf(0.975, s + 0.5, n - s + 0.5))
        raw_ci_low.append(lo)
        raw_ci_high.append(hi)
    out["no_pooling_ci_low"] = raw_ci_low
    out["no_pooling_ci_high"] = raw_ci_high

    # 2. Complete Pooling (Single global average)
    total_s = float(np.sum(s_arr))
    total_n = float(np.sum(n_arr))
    global_mean = total_s / total_n
    out["complete_pooling_mean"] = global_mean

    # 3. Partial Pooling (Hierarchical Beta-Binomial via Empirical Bayes MAP)
    def neg_log_marginal_posterior(params: np.ndarray) -> float:
        log_mu_logit, log_kappa = params
        mu = float(special.expit(log_mu_logit))
        kappa = float(np.exp(log_kappa))
        a0 = mu * kappa
        b0 = (1.0 - mu) * kappa
        # Beta-Binomial log likelihood across all categories
        ll = np.sum(
            special.gammaln(n_arr + 1.0)
            - special.gammaln(s_arr + 1.0)
            - special.gammaln(n_arr - s_arr + 1.0)
            + special.betaln(s_arr + a0, n_arr - s_arr + b0)
            - special.betaln(a0, b0)
        )
        # Weakly regularizing hyperprior on kappa ~ Gamma(shape=2.5, rate=0.15)
        log_prior = 1.5 * np.log(kappa) - 0.15 * kappa
        return -float(ll + log_prior)

    opt_res = optimize.minimize(
        neg_log_marginal_posterior,
        x0=np.array([special.logit(global_mean), np.log(15.0)]),
        method="BFGS",
    )
    prior_mu = float(special.expit(opt_res.x[0]))
    prior_kappa = float(np.exp(opt_res.x[1]))
    alpha_0 = prior_mu * prior_kappa
    beta_0 = (1.0 - prior_mu) * prior_kappa

    # Posterior per category j: Beta(alpha_0 + S_j, beta_0 + N_j - S_j)
    post_alpha = alpha_0 + s_arr
    post_beta = beta_0 + (n_arr - s_arr)
    out["partial_pooling_mean"] = post_alpha / (post_alpha + post_beta)
    out["partial_pooling_ci_low"] = stats.beta.ppf(0.025, post_alpha, post_beta)
    out["partial_pooling_ci_high"] = stats.beta.ppf(0.975, post_alpha, post_beta)
    out["shrinkage_factor"] = prior_kappa / (prior_kappa + n_arr)

    hyperparams = {
        "alpha_0": alpha_0,
        "beta_0": beta_0,
        "prior_mean": prior_mu,
        "prior_concentration_kappa": prior_kappa,
        "complete_pooling_global_mean": global_mean,
    }
    return out, hyperparams
