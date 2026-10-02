"""Standalone runnable script for 02_data_hygiene_and_overfitting."""
import matplotlib
matplotlib.use('Agg')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from agent_stats.ch02_hygiene_overfitting import (
    HoldoutGate,
    generate_synthetic_benchmark,
    run_prompt_hill_climbing_simulation,
    stratified_benchmark_split,
)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120

df_bench = generate_synthetic_benchmark(num_tasks=200, random_state=42)
opt_df, holdout_df = stratified_benchmark_split(df_bench, holdout_fraction=0.40, random_state=42)
print(f"Total Tasks: {len(df_bench)} | Optimization Set (60%): {len(opt_df)} | Holdout Set (40%): {len(holdout_df)}")

comparison = pd.DataFrame({
    "Opt Set Share (%)": (opt_df["stratum"].value_counts(normalize=True) * 100).round(1),
    "Holdout Set Share (%)": (holdout_df["stratum"].value_counts(normalize=True) * 100).round(1),
    "Opt Count": opt_df["stratum"].value_counts(),
    "Holdout Count": holdout_df["stratum"].value_counts(),
}).sort_index()
comparison

history_df, gate = run_prompt_hill_climbing_simulation(opt_df, holdout_df, num_steps=30, random_state=42)

# Identify the divergence point where Ungated Opt - Ungated Holdout exceeds 5 percentage points
gen_gap = history_df["ungated_opt_pass_rate"] - history_df["ungated_holdout_pass_rate"]
divergence_step = int(history_df.loc[gen_gap > 0.05, "step"].iloc[0])

print(f"Overfitting Divergence Point detected at Step {divergence_step}!")
print(f"Final Ungated Optimization Pass Rate : {history_df['ungated_opt_pass_rate'].iloc[-1]:.1%}")
print(f"Final Ungated Holdout Pass Rate      : {history_df['ungated_holdout_pass_rate'].iloc[-1]:.1%} (Overfit Collapse!)")
print(f"Final Holdout-Gated Holdout Pass Rate: {history_df['gated_holdout_pass_rate'].iloc[-1]:.1%} (Protected Generalization!)")

history_df[["step", "mutation_type", "ungated_opt_pass_rate", "ungated_holdout_pass_rate", "gated_holdout_pass_rate", "gated_accepted", "gate_reason"]].tail(12)

fig, ax = plt.subplots(figsize=(11, 5.8))

steps = history_df["step"]
ax.plot(steps, history_df["ungated_opt_pass_rate"], "o--", color="#d95f02", linewidth=2.2, label="Ungated Optimizer — Optimization Set (60%)")
ax.plot(steps, history_df["ungated_holdout_pass_rate"], "s-", color="#e7298a", linewidth=2.5, label="Ungated Optimizer — Unseen Holdout Set (40%) [Overfits!]")
ax.plot(steps, history_df["gated_holdout_pass_rate"], "^-", color="#1b9e77", linewidth=2.8, label="HoldoutGate Optimizer — Unseen Holdout Set (40%) [Protected]")

ax.axvline(divergence_step, color="#333333", linestyle=":", linewidth=1.8, label=f"Overfitting Divergence Point (Step {divergence_step})")
ax.fill_between(
    steps,
    history_df["ungated_holdout_pass_rate"],
    history_df["ungated_opt_pass_rate"],
    where=(steps >= divergence_step),
    color="#d95f02",
    alpha=0.15,
    label="Goodhart Generalization Gap (Reward Hacking)",
)

ax.set_title("Goodhart's Law in Prompt Hill-Climbing: Optimization vs. Holdout Pass Rates", fontsize=13, fontweight="bold")
ax.set_xlabel("Prompt Mutation Iteration Step")
ax.set_ylabel("Benchmark Pass Rate")
ax.set_ylim(0.45, 0.95)
ax.legend(loc="upper left", fontsize=9.5)

plt.tight_layout()
plt.savefig("figures/ch02_goodharts_law_holdout_gate.png", dpi=150, bbox_inches="tight")
plt.show()
