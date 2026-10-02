"""Standalone runnable script for 03_frequentist_ab_testing."""
import matplotlib
matplotlib.use('Agg')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from agent_stats.ch03_frequentist_ab import (
    calculate_required_sample_size,
    independent_two_sample_z_test,
    mcnemar_test,
    run_monte_carlo_power_comparison,
    simulate_paired_experiment,
    wilcoxon_signed_rank_test,
)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120

# 1. Power Analysis Calculator: detecting +5% lift (65% -> 70%) at alpha=0.05, power=0.80
n_unpaired = calculate_required_sample_size(0.65, 0.70, alpha=0.05, power=0.80)
n_paired_high_corr = calculate_required_sample_size(0.65, 0.70, alpha=0.05, power=0.80, paired_correlation=0.88)

print(f"Required tasks (Unpaired 2-Sample Z-Test) : {n_unpaired:,} tasks per arm")
print(f"Required tasks (Paired McNemar, rho=0.88) : {n_paired_high_corr:,} paired tasks ({n_unpaired / n_paired_high_corr:.1f}x sample reduction!)")

exp = simulate_paired_experiment(num_tasks=160, p_baseline=0.65, p_candidate=0.70, discordant_noise=0.010, random_state=7)
a, b, c, d = exp.contingency_table.ravel()

mc_res = mcnemar_test(exp.baseline_pass, exp.candidate_pass, continuity_correction=True)
z_res = independent_two_sample_z_test(exp.baseline_pass, exp.candidate_pass)
wilcox_res = wilcoxon_signed_rank_test(exp.baseline_tokens, exp.candidate_tokens)

print("=== 2x2 PAIRED CONTINGENCY TABLE (N=160) ===")
print(pd.DataFrame(
    exp.contingency_table,
    index=["Baseline PASS (1)", "Baseline FAIL (0)"],
    columns=["Candidate PASS (1)", "Candidate FAIL (0)"],
))
print()
print(f"Observed Pass Rates      : Baseline = {z_res['p1']:.2%} | Candidate = {z_res['p2']:.2%} (Lift = {(z_res['p2']-z_res['p1'])*100:+.2f} pp)")
print(f"McNemar's Paired Test    : chi2 = {mc_res['statistic']:.3f}, p = {mc_res['p_value']:.4f} (b={b} regressions, c={c} fixes) -> {'SIGNIFICANT' if mc_res['p_value'] < 0.05 else 'NOT SIGNIFICANT'}")
print(f"Unpaired 2-Sample Z-Test : z    = {z_res['z_stat']:.3f}, p = {z_res['p_value']:.4f} -> {'SIGNIFICANT' if z_res['p_value'] < 0.05 else 'FAILS TO DETECT!'}")
print(f"Wilcoxon Token Test      : stat = {wilcox_res['statistic']:.1f}, p = {wilcox_res['p_value']:.4e} (Median {wilcox_res['median_baseline']:.0f} -> {wilcox_res['median_candidate']:.0f} tokens)")

sample_sizes = [40, 80, 120, 160, 200, 250, 350, 500, 750, 1000, 1400]
power_df = run_monte_carlo_power_comparison(
    sample_sizes=sample_sizes,
    p_baseline=0.65,
    p_candidate=0.70,
    discordant_noise=0.008,
    num_trials=1000,
    alpha=0.05,
    random_state=42,
)

fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))

# Left plot: Empirical Power Curve (1,000 Monte Carlo runs)
axes[0].plot(power_df["sample_size"], power_df["mcnemar_paired_power"], "o-", color="#1b9e77", linewidth=2.6, label="McNemar's Paired Test (Same Tasks)")
axes[0].plot(power_df["sample_size"], power_df["unpaired_z_power"], "s--", color="#d95f02", linewidth=2.4, label="Independent 2-Sample Z-Test (Unpaired)")
axes[0].axhline(0.80, color="#333333", linestyle=":", linewidth=1.8, label="80% Target Power Threshold")
axes[0].set_title("Monte Carlo Power Curve (+5% Lift, 1,000 Trials/N)", fontsize=12, fontweight="bold")
axes[0].set_xlabel("Benchmark Sample Size (N Tasks)")
axes[0].set_ylabel("Empirical Power (Probability of Detecting True +5% Lift)")
axes[0].set_ylim(0.0, 1.05)
axes[0].legend(loc="lower right")

# Right plot: Skewed Token Usage Distribution (Wilcoxon Signed-Rank illustration)
sns.kdeplot(exp.baseline_tokens, fill=True, color="#e7298a", alpha=0.35, ax=axes[1], label=f"Baseline Tokens (Median={np.median(exp.baseline_tokens):.0f})")
sns.kdeplot(exp.candidate_tokens, fill=True, color="#1b9e77", alpha=0.35, ax=axes[1], label=f"Candidate Tokens (Median={np.median(exp.candidate_tokens):.0f})")
axes[1].set_title(f"Skewed Token Usage Distribution (Wilcoxon p = {wilcox_res['p_value']:.2e})", fontsize=12, fontweight="bold")
axes[1].set_xlabel("Tokens Consumed per Task")
axes[1].set_ylabel("Density")
axes[1].set_xlim(0, 8000)
axes[1].legend()

plt.tight_layout()
plt.savefig("figures/ch03_mcnemar_power_and_wilcoxon.png", dpi=150, bbox_inches="tight")
plt.show()

power_df
