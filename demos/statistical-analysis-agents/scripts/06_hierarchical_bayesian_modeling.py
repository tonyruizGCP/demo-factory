"""Standalone runnable script for 06_hierarchical_bayesian_modeling."""
import matplotlib
matplotlib.use('Agg')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from agent_stats.ch06_hierarchical_bayes import (
    fit_hierarchical_beta_binomial,
    get_sparse_category_dataset,
)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120

df_raw = get_sparse_category_dataset()
df_est, hyper = fit_hierarchical_beta_binomial(df_raw)

print(f"Estimated Population Hyperprior: alpha_0 = {hyper['alpha_0']:.2f}, beta_0 = {hyper['beta_0']:.2f}")
print(f"Hyperprior Mean (mu_0) = {hyper['prior_mean']:.1%} | Prior Concentration (kappa) = {hyper['prior_concentration_kappa']:.1f} pseudo-trials")

df_est[[
    "category", "N", "S", "true_latent_rate",
    "no_pooling_mean", "complete_pooling_mean", "partial_pooling_mean", "shrinkage_factor"
]].round(3)

fig, ax = plt.subplots(figsize=(12, 6.2))

y_pos = np.arange(len(df_est))
offset = 0.16

# Plot No-Pooling Raw Estimates + 95% Interval
ax.errorbar(
    df_est["no_pooling_mean"],
    y_pos - offset,
    xerr=[
        df_est["no_pooling_mean"] - df_est["no_pooling_ci_low"],
        df_est["no_pooling_ci_high"] - df_est["no_pooling_mean"],
    ],
    fmt="o",
    color="#d95f02",
    ecolor="#d95f02",
    elinewidth=1.8,
    capsize=4,
    label="No Pooling (Raw S_j / N_j + 95% CI)",
)

# Plot Partial-Pooling Hierarchical Estimates + 95% Credible Interval
ax.errorbar(
    df_est["partial_pooling_mean"],
    y_pos + offset,
    xerr=[
        df_est["partial_pooling_mean"] - df_est["partial_pooling_ci_low"],
        df_est["partial_pooling_ci_high"] - df_est["partial_pooling_mean"],
    ],
    fmt="s",
    color="#1b9e77",
    ecolor="#1b9e77",
    elinewidth=2.4,
    capsize=4,
    label="Partial Pooling (Hierarchical Shrinkage + 95% CrI)",
)

# Plot True Latent Rates for ground-truth reference
ax.scatter(
    df_est["true_latent_rate"],
    y_pos,
    marker="*",
    s=130,
    color="#222222",
    zorder=5,
    label="True Underlying Category Capability",
)

ax.axvline(hyper["prior_mean"], color="#377eb8", linestyle="--", linewidth=1.8, label=f"Hyperprior Mean ({hyper['prior_mean']:.1%})")

labels = [f"{row['category']}\n(S={row['S']}/{row['N']}, shrink={row['shrinkage_factor']:.0%})" for _, row in df_est.iterrows()]
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=9.5)
ax.set_xlabel("Category Pass Rate")
ax.set_xlim(-0.03, 1.03)
ax.set_title("Hierarchical Bayesian Shrinkage vs. Raw Empirical Pass Rates Across Sparse Categories", fontsize=12.5, fontweight="bold")
ax.legend(loc="lower left", fontsize=9.5)

plt.tight_layout()
plt.savefig("figures/ch06_hierarchical_forest_plot.png", dpi=150, bbox_inches="tight")
plt.show()

rmse_raw = np.sqrt(np.mean((df_est["no_pooling_mean"] - df_est["true_latent_rate"]) ** 2))
rmse_shrunk = np.sqrt(np.mean((df_est["partial_pooling_mean"] - df_est["true_latent_rate"]) ** 2))

race_row = df_est.loc[df_est["category"] == "distributed_race_condition"].iloc[0]
mem_row = df_est.loc[df_est["category"] == "memory_leak"].iloc[0]

print("=== EDGE-CASE REGRESSION TRIAGE CASE STUDY ===")
print(f"1. `distributed_race_condition` (S=0/3): Raw = {race_row['no_pooling_mean']:.1%} -> Hierarchical = {race_row['partial_pooling_mean']:.1%} "
      f"(95% CrI: [{race_row['partial_pooling_ci_low']:.1%}, {race_row['partial_pooling_ci_high']:.1%}], True = {race_row['true_latent_rate']:.1%})")
print(f"2. `memory_leak` (S=1/4)               : Raw = {mem_row['no_pooling_mean']:.1%} -> Hierarchical = {mem_row['partial_pooling_mean']:.1%} "
      f"(95% CrI: [{mem_row['partial_pooling_ci_low']:.1%}, {mem_row['partial_pooling_ci_high']:.1%}], True = {mem_row['true_latent_rate']:.1%})")
print(f"3. Estimation Error (RMSE vs True Rate): No-Pooling RMSE = {rmse_raw:.3f} vs. Partial-Pooling RMSE = {rmse_shrunk:.3f} "
      f"({(1 - rmse_shrunk/rmse_raw)*100:.1f}% error reduction!)")
