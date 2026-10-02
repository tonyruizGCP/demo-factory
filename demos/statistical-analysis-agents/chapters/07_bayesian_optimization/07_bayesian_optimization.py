"""Standalone runnable script for 07_bayesian_optimization."""
import matplotlib
matplotlib.use('Agg')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from agent_stats.ch07_bayesian_optimization import (
    evaluate_harness_config,
    expected_improvement,
    run_bayesian_optimization_loop,
    upper_confidence_bound,
)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120

bo_res = run_bayesian_optimization_loop(
    n_init=5,
    n_total_trials=25,
    acquisition_type="EI",
    snapshot_iterations=(5, 12, 25),
    random_state=42,
)

print("=== BAYESIAN OPTIMIZATION CONVERGENCE SUMMARY (25 TRIALS) ===")
print(f"True Unknown Global Optimum : reasoning_tokens = {bo_res['true_optimum']['reasoning_tokens']:.0f}, "
      f"context_limit = {bo_res['true_optimum']['context_limit_k']:.1f}k -> Score = {bo_res['true_optimum']['true_score']:.4f}")
print(f"Discovered Optimum (Trial {bo_res['discovered_optimum']['trial']:2d}): reasoning_tokens = {bo_res['discovered_optimum']['reasoning_tokens']:.0f}, "
      f"context_limit = {bo_res['discovered_optimum']['context_limit_k']:.1f}k -> Score = {bo_res['discovered_optimum']['observed_score']:.4f}")

bo_res["history_df"].tail(10)

rr = bo_res["r_grid"]
cc = bo_res["c_grid"]
snap_steps = [5, 12, 25]

fig, axes = plt.subplots(len(snap_steps), 2, figsize=(14, 12.5))

for row_idx, step in enumerate(snap_steps):
    snap = bo_res["snapshots"][step]
    x_obs = snap["x_observed"]
    next_pt = snap["next_point"]

    # Left column: GP Posterior Mean Surface + Uncertainty Contour + Sampled Points
    ax_mean = axes[row_idx, 0]
    c1 = ax_mean.contourf(rr, cc, snap["mu_surface"], levels=18, cmap="viridis")
    cs_std = ax_mean.contour(rr, cc, snap["std_surface"], levels=6, colors="white", linewidths=0.8, linestyles="--")
    ax_mean.clabel(cs_std, inline=True, fontsize=7.5, fmt="std=%.3f")
    ax_mean.scatter(x_obs[:, 0], x_obs[:, 1], c="white", edgecolor="black", s=55, zorder=4, label="Evaluated Trials")
    ax_mean.scatter([bo_res["true_optimum"]["reasoning_tokens"]], [bo_res["true_optimum"]["context_limit_k"]],
                    c="yellow", edgecolor="black", marker="*", s=160, zorder=5, label="True Global Optimum")
    plt.colorbar(c1, ax=ax_mean, label="GP Mean Score")
    ax_mean.set_title(f"Trial {step:02d}: GP Predicted Mean & Uncertainty (white dashed)", fontsize=11, fontweight="bold")
    ax_mean.set_xlabel("Reasoning Tokens")
    ax_mean.set_ylabel("Context Limit (k tokens)")
    ax_mean.legend(loc="lower right", fontsize=8)

    # Right column: Expected Improvement (EI) Acquisition Surface + Next Chosen Coordinate
    ax_acq = axes[row_idx, 1]
    c2 = ax_acq.contourf(rr, cc, snap["acq_surface"], levels=18, cmap="magma")
    ax_acq.scatter(x_obs[:, 0], x_obs[:, 1], c="white", edgecolor="black", s=45, alpha=0.7, label="Past Samples")
    ax_acq.scatter([next_pt[0]], [next_pt[1]], c="#00ffcc", edgecolor="black", marker="P", s=160, zorder=6,
                   label=f"Next Sample ({next_pt[0]:.0f}, {next_pt[1]:.1f}k)")
    plt.colorbar(c2, ax=ax_acq, label="Expected Improvement (EI)")
    ax_acq.set_title(f"Trial {step:02d}: Acquisition Surface (EI) & Next Query Point", fontsize=11, fontweight="bold")
    ax_acq.set_xlabel("Reasoning Tokens")
    ax_acq.set_ylabel("Context Limit (k tokens)")
    ax_acq.legend(loc="lower right", fontsize=8)

plt.tight_layout()
plt.savefig("figures/ch07_bayesian_optimization_surfaces.png", dpi=150, bbox_inches="tight")
plt.show()
