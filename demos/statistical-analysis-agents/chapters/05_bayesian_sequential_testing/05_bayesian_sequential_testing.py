"""Standalone runnable script for 05_bayesian_sequential_testing."""
import matplotlib
matplotlib.use('Agg')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

from agent_stats.ch05_bayesian_sequential import (
    BetaBinomialEvaluator,
    prob_superiority_monte_carlo,
    prob_superiority_quadrature,
    run_compute_savings_benchmark,
    update_beta_posterior,
)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120

# Verify Monte Carlo vs Exact Numerical Quadrature agreement
a_c, b_c = update_beta_posterior(1.0, 1.0, successes=58, trials=75)
a_b, b_b = update_beta_posterior(1.0, 1.0, successes=47, trials=75)
p_mc = prob_superiority_monte_carlo(a_c, b_c, a_b, b_b, num_samples=100_000)
p_quad = prob_superiority_quadrature(a_c, b_c, a_b, b_b)
print(f"P(theta_cand > theta_base | D) -> Quadrature: {p_quad:.5f} | Monte Carlo: {p_mc:.5f} (|diff| = {abs(p_quad - p_mc):.5f})")

# 1. Step-by-step trajectory of a Strong Candidate (p=0.77) vs Baseline (p=0.65)
rng = np.random.default_rng(12)
evaluator = BetaBinomialEvaluator(accept_threshold=0.95, abandon_threshold=0.10, min_trials_before_stopping=15, use_quadrature=True)

snapshots = {}
for t in range(1, 201):
    c_pass = int(rng.random() < 0.77)
    b_pass = int(rng.random() < 0.65)
    status = evaluator.step(c_pass, b_pass)
    if t in (10, 35, 70) or status != "CONTINUE":
        snapshots[t] = (evaluator.alpha_cand, evaluator.beta_cand, evaluator.alpha_base, evaluator.beta_base, evaluator.history[-1]["prob_superiority"], status)
    if status != "CONTINUE":
        print(f"Sequential Evaluator terminated at Trial {t} with decision: {status} (P_sup = {evaluator.history[-1]['prob_superiority']:.3f})")
        break

# 2. Compute-Savings Benchmark across 100 Weak Variants + 10 Strong Variants (Fixed N=500 vs Sequential)
bench = run_compute_savings_benchmark(
    num_weak_variants=100,
    num_strong_variants=10,
    max_trials_per_variant=500,
    p_baseline=0.65,
    accept_threshold=0.95,
    abandon_threshold=0.10,
    random_state=42,
)

print(f"Fixed N=500 Total Trials      : {bench['fixed_total_trials']:,} trials")
print(f"Sequential Stopping Trials    : {bench['sequential_total_trials']:,} trials")
print(f"Total Compute / Token Savings : {bench['compute_savings_pct']:.1f}% ({bench['trials_saved']:,} fewer trials!)")
print(f"Avg Trials per Weak Variant   : {bench['weak_avg_trials']:.1f} trials (vs 500)")
print(f"Avg Trials per Strong Variant : {bench['strong_avg_trials']:.1f} trials (vs 500)")

fig, axes = plt.subplots(1, 2, figsize=(15, 5.6))

# Left Plot: Posterior Beta Density Shifts as task results arrive
x_grid = np.linspace(0.35, 0.98, 400)
palette = ["#7570b3", "#377eb8", "#1b9e77"]
for (t, (ac, bc, ab, bb, psup, st)), col in zip(list(snapshots.items())[:3], palette):
    axes[0].plot(x_grid, stats.beta.pdf(x_grid, ac, bc), "-", color=col, linewidth=2.3, label=f"Candidate @ N={t} (P_sup={psup:.2f}, {st})")
    axes[0].plot(x_grid, stats.beta.pdf(x_grid, ab, bb), "--", color=col, linewidth=1.6, alpha=0.75, label=f"Baseline @ N={t}")

axes[0].set_title("Posterior Beta Distribution Shifts Over Sequential Trials", fontsize=12, fontweight="bold")
axes[0].set_xlabel("Latent Success Probability (theta)")
axes[0].set_ylabel("Posterior Density")
axes[0].legend(fontsize=8.5, loc="upper left")

# Right Plot: Bar Chart of Compute/Token Savings (Fixed N=500 vs Sequential Stopping)
categories = ["All 110 Variants\n(Total Trials)", "100 Weak Variants\n(Trials / Variant)", "10 Strong Variants\n(Trials / Variant)"]
fixed_vals = [bench["fixed_total_trials"] / 110.0, 500.0, 500.0]
seq_vals = [
    bench["sequential_total_trials"] / 110.0,
    bench["weak_avg_trials"],
    bench["strong_avg_trials"],
]

x = np.arange(len(categories))
width = 0.36
bars1 = axes[1].bar(x - width / 2, fixed_vals, width, label="Fixed Horizon (N=500)", color="#d95f02", alpha=0.85)
bars2 = axes[1].bar(x + width / 2, seq_vals, width, label="Bayesian Early Stopping", color="#1b9e77", alpha=0.90)

for b1, b2 in zip(bars1, bars2):
    sav = (1.0 - b2.get_height() / b1.get_height()) * 100.0
    axes[1].text(b2.get_x() + b2.get_width() / 2, b2.get_height() + 12, f"-{sav:.1f}%", ha="center", fontweight="bold", color="#1b9e77")

axes[1].set_title(f"Compute & Token Savings: {bench['compute_savings_pct']:.1f}% Reduction vs. Fixed N=500", fontsize=12, fontweight="bold")
axes[1].set_xticks(x)
axes[1].set_xticklabels(categories)
axes[1].set_ylabel("Average Evaluation Trials per Variant")
axes[1].set_ylim(0, 580)
axes[1].legend()

plt.tight_layout()
plt.savefig("figures/ch05_bayesian_sequential_stopping.png", dpi=150, bbox_inches="tight")
plt.show()
