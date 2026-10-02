"""Standalone runnable script for 01_stochasticity_trap."""
import matplotlib
matplotlib.use('Agg')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.special import comb

from agent_stats.ch01_stochasticity import (
    AgentStochasticitySimulator,
    calculate_pass_at_k,
    calculate_pass_pow_k,
)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120
print("Loaded Chapter 1 Stochasticity Engine successfully.")

sim = AgentStochasticitySimulator(num_tasks=200, num_seeds=20, random_state=42)

profiles = [
    sim.simulate_agent("Consistent Deterministic Agent (noise=0.12)", baseline_capability=0.75, execution_noise=0.12, seed_offset=1),
    sim.simulate_agent("Moderate Production Agent (noise=0.45)", baseline_capability=0.75, execution_noise=0.45, seed_offset=2),
    sim.simulate_agent("Lucky Flaky Agent (noise=0.85)", baseline_capability=0.75, execution_noise=0.85, seed_offset=3),
]

k_vals = list(range(1, 11))
summary_rows = []
for prof in profiles:
    p_at_k = prof.pass_at_k_curve(k_vals)
    p_pow_k = prof.pass_pow_k_curve(k_vals)
    summary_rows.append({
        "Agent Profile": prof.name,
        "Pass@1": f"{p_at_k[0]:.1%}",
        "Pass@5": f"{p_at_k[4]:.1%}",
        "Pass@10": f"{p_at_k[9]:.1%}",
        "Pass^5 (5-in-a-row)": f"{p_pow_k[4]:.1%}",
        "Pass^10 (10-in-a-row)": f"{p_pow_k[9]:.1%}",
        "Consistency Delta (Pass@1 - Pass^5)": f"{(p_at_k[0] - p_pow_k[4]):.1%}",
    })

pd.DataFrame(summary_rows)

fig, axes = plt.subplots(1, 2, figsize=(15, 5.8))

# Plot 1: Pass@k vs Pass^k curves for k = 1..10
colors = ["#1b9e77", "#377eb8", "#d95f02"]
for prof, color in zip(profiles, colors):
    p_at_k = prof.pass_at_k_curve(k_vals)
    p_pow_k = prof.pass_pow_k_curve(k_vals)
    axes[0].plot(k_vals, p_at_k, marker="o", linestyle="--", color=color, linewidth=2.2, label=f"{prof.name.split(' (')[0]} — Pass@k")
    axes[0].plot(k_vals, p_pow_k, marker="s", linestyle="-", color=color, linewidth=2.5, label=f"{prof.name.split(' (')[0]} — Pass^k")

axes[0].set_title("Pass@k (Optimistic) vs. Pass^k (Consistent) across k=1..10", fontsize=12, fontweight="bold")
axes[0].set_xlabel("Number of Trials (k)")
axes[0].set_ylabel("Task Success / Consistency Probability")
axes[0].set_xticks(k_vals)
axes[0].set_ylim(0.0, 1.05)
axes[0].legend(fontsize=8.5, loc="lower left")

# Plot 2: Heatmap of Consistency Delta (Pass@1 - Pass^5) across noise & baseline capability
capabilities = np.linspace(0.30, 0.90, 7)
noise_levels = np.linspace(0.10, 0.90, 7)
delta_grid = sim.consistency_delta_grid(capabilities, noise_levels, k=5)

sns.heatmap(
    delta_grid,
    annot=True,
    fmt=".2f",
    cmap="YlOrRd",
    xticklabels=[f"{c:.0%}" for c in capabilities],
    yticklabels=[f"{n:.2f}" for n in noise_levels],
    cbar_kws={"label": "Consistency Delta (Pass@1 - Pass^5)"},
    ax=axes[1],
)
axes[1].set_title("Consistency Delta Heatmap: Pass@1 - Pass^5", fontsize=12, fontweight="bold")
axes[1].set_xlabel("Baseline Capability (Pass@1)")
axes[1].set_ylabel("Execution Noise / Stochasticity")
axes[1].invert_yaxis()

plt.tight_layout()
plt.savefig("figures/ch01_pass_at_k_vs_pass_pow_k.png", dpi=150, bbox_inches="tight")
plt.show()

prompt_a = sim.simulate_agent("Prompt A (High-Variance Explorer)", baseline_capability=0.76, execution_noise=0.80, seed_offset=101)
prompt_b = sim.simulate_agent("Prompt B (Structured Deterministic)", baseline_capability=0.74, execution_noise=0.10, seed_offset=202)

# Single-run Pass@1 on Seed #0
seed0_a = prompt_a.trial_matrix[:, 0].mean()
seed0_b = prompt_b.trial_matrix[:, 0].mean()

# Multi-seed Unbiased Pass@5 and Pass^5 across n=20 seeds
pass_at_5_a = np.mean(calculate_pass_at_k(20, prompt_a.success_counts, 5))
pass_at_5_b = np.mean(calculate_pass_at_k(20, prompt_b.success_counts, 5))
pass_pow_5_a = np.mean(calculate_pass_pow_k(20, prompt_a.success_counts, 5))
pass_pow_5_b = np.mean(calculate_pass_pow_k(20, prompt_b.success_counts, 5))

print("=== HANDS-ON PROMPT SELECTION AUDIT ===")
print(f"Single-Run Pass@1 (Seed 0) -> Prompt A: {seed0_a:.1%} | Prompt B: {seed0_b:.1%}")
print(f"  [Naive Decision]: Picks {'Prompt A' if seed0_a > seed0_b else 'Prompt B'} based on a single eval run!")
print("-" * 65)
print(f"Unbiased Pass@5 (Best of 5) -> Prompt A: {pass_at_5_a:.1%} | Prompt B: {pass_at_5_b:.1%}")
print(f"Unbiased Pass^5 (5/5 Rel.)  -> Prompt A: {pass_pow_5_a:.1%} | Prompt B: {pass_pow_5_b:.1%}")
print(f"  [Production Decision]: Picks {'Prompt B' if pass_pow_5_b > pass_pow_5_a else 'Prompt A'} (+{(pass_pow_5_b - pass_pow_5_a)*100:.1f} pp higher 5-run reliability!)")
