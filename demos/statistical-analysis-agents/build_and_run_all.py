"""Generates and executes all 8 Jupyter Notebooks (.ipynb) and standalone Python scripts (.py)."""

from __future__ import annotations

from pathlib import Path
import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook
from nbclient import NotebookClient


ROOT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
FIGURES_DIR = ROOT_DIR / "figures"
PROMPTS_DIR = ROOT_DIR / "prompts"


def make_notebook(cells: list) -> nbformat.NotebookNode:
    nb = new_notebook()
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.metadata["language_info"] = {
        "name": "python",
        "version": "3.13",
    }
    nb.cells = cells
    return nb


def build_chapter_01() -> tuple[str, list]:
    md_intro = new_markdown_cell(
        r"""# Chapter 1: The Stochasticity Trap ($\text{Pass}@k$ vs. $\text{Pass}^k$)

When evaluating AI agents across multi-turn tool-calling trajectories, **temperature sampling**, **tool latency**, and **non-deterministic environment states** introduce substantial execution variance. Two metrics capture fundamentally opposite operational goals:

---

## 1. Mathematical Derivations

### A. $\text{Pass}@k$: The Optimistic Capability (Best-of-$k$) Estimator
$\text{Pass}@k$ measures the probability that **at least one** out of $k$ independent rollouts succeeds on a task. If a task has true latent success probability $p_i$, then theoretically:
$$\text{Pass}@k_i = 1 - (1 - p_i)^k$$

Directly computing $1 - (1 - \hat{p}_i)^k$ from a small sample produces severe upward variance. Instead, **Chen et al. (2021)** derived the **unbiased combinatorial estimator** by drawing $n \ge k$ total trials per task and counting $c$ successes:
$$\widehat{\text{Pass}@k} = 1 - \frac{\binom{n - c}{k}}{\binom{n}{k}}$$

*Why is it unbiased?* The term $\frac{\binom{n - c}{k}}{\binom{n}{k}}$ is the exact hypergeometric probability of drawing $k$ failures out of $n$ trials when $n - c$ failures exist. Its expectation over $c \sim \text{Binomial}(n, p_i)$ is $(1 - p_i)^k$.

---

### B. $\text{Pass}^k$: The Consistency & Production Reliability Estimator
Introduced in **$\tau$-bench (Yao et al., 2024)**, $\text{Pass}^k$ measures the probability that **all $k$** independent rollouts succeed on the task:
$$\text{Pass}^k_i = p_i^k$$

Using the same $n$ trials and $c$ successes ($k \le n$), the **unbiased combinatorial estimator** for $p_i^k$ is the probability that a random subset of size $k$ drawn without replacement contains **only successes**:
$$\widehat{\text{Pass}^k}_{\text{unbiased}} = \frac{\binom{c}{k}}{\binom{n}{k}}, \qquad \widehat{\text{Pass}^k}_{\text{plugin}} = \left(\frac{c}{n}\right)^k$$

> **The Trap**: As $k \to \infty$, $\text{Pass}@k$ monotonically **inflates** toward $1.0$ for any flaky agent ($p_i > 0$), whereas $\text{Pass}^k$ exponentially **decays** toward $0.0$ unless $p_i \approx 1.0$. Relying on $\text{Pass}@k$ (or single-seed $\text{Pass}@1$) masks catastrophic production flakiness!"""
    )

    code_setup = new_code_cell(
        """import numpy as np
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
print("Loaded Chapter 1 Stochasticity Engine successfully.")"""
    )

    md_sim = new_markdown_cell(
        r"""## 2. Simulation Engine & Metric Implementations

Below we instantiate `AgentStochasticitySimulator` across $N=200$ benchmark tasks and $n=20$ repeated seeds per task, comparing three distinct agent profiles:
1. **Consistent Deterministic Agent**: Baseline capability $= 75\%$, Low execution noise ($\sigma = 0.12$).
2. **Moderate Production Agent**: Baseline capability $= 75\%$, Moderate execution noise ($\sigma = 0.45$).
3. **Lucky Flaky Agent**: Baseline capability $= 75\%$, High execution noise ($\sigma = 0.85$).

Notice that **all three agents have the exact same $\text{Pass}@1 \approx 75\%$!**"""
    )

    code_sim = new_code_cell(
        """sim = AgentStochasticitySimulator(num_tasks=200, num_seeds=20, random_state=42)

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

pd.DataFrame(summary_rows)"""
    )

    md_viz = new_markdown_cell(
        """## 3. Visualizations: $\\text{Pass}@k$ vs. $\\text{Pass}^k$ Divergence & Consistency Delta Heatmap"""
    )

    code_viz = new_code_cell(
        """fig, axes = plt.subplots(1, 2, figsize=(15, 5.8))

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
plt.show()"""
    )

    md_exercise = new_markdown_cell(
        r"""## 4. Interactive Hands-on Exercise: Choosing Between Two Prompt Variants

Suppose you are evaluating two candidate system prompts for a production customer-support agent:
- **Prompt Variant A ("Aggressive Explorer")**: Mean capability $= 76\%$, but high temperature/tool-selection variance (`execution_noise = 0.80`).On a single lucky seed, it can spike up to **79.5% $\text{Pass}@1$**.
- **Prompt Variant B ("Structured Deterministic")**: Mean capability $= 74\%$, with strict schema constraints (`execution_noise = 0.10`).

Let's simulate how a developer running a **single-seed $\text{Pass}@1$ eval** gets tricked into shipping Prompt A, whereas a **$k=5$ $\text{Pass}^k$ consistency check** exposes Prompt A's catastrophic flakiness ($26\%$ $\text{Pass}^5$ vs. $66\%$ for Prompt B)."""
    )

    code_exercise = new_code_cell(
        """prompt_a = sim.simulate_agent("Prompt A (High-Variance Explorer)", baseline_capability=0.76, execution_noise=0.80, seed_offset=101)
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
print(f"  [Production Decision]: Picks {'Prompt B' if pass_pow_5_b > pass_pow_5_a else 'Prompt A'} (+{(pass_pow_5_b - pass_pow_5_a)*100:.1f} pp higher 5-run reliability!)")"""
    )

    script_code = "\n\n".join([c.source for c in [code_setup, code_sim, code_viz, code_exercise]])
    return script_code, [md_intro, code_setup, md_sim, code_sim, md_viz, code_viz, md_exercise, code_exercise]


def build_chapter_02() -> tuple[str, list]:
    md_intro = new_markdown_cell(
        r"""# Chapter 2: Data Hygiene & Overfitting Prevention

> *"When a measure becomes a target, it ceases to be a good measure."* — **Goodhart's Law**

When automated prompt optimizers (or human engineers) iteratively hill-climb on a fixed benchmark without a strict **Holdout Gate**, mutations quickly transition from **genuine reasoning improvements** to **reward hacking** (e.g., overfitting to specific task phrasing, memorizing edge-case regexes, or biasing toward tool schemas over-represented in the training split).

---

## 1. Mathematical & Experimental Formulation

Let a benchmark $\mathcal{D}$ of $N=200$ tasks be partitioned into an **Optimization Set** $\mathcal{D}_{\text{opt}}$ ($60\%, n=120$) and an **Unseen Holdout Set** $\mathcal{D}_{\text{hold}}$ ($40\%, n=80$) via **joint stratification** over Difficulty Tier $D \in \{\text{Easy}, \text{Medium}, \text{Hard}\}$ and Capability Tag $C \in \{\text{tool\_selection}, \text{context\_retrieval}, \text{code\_execution}\}$:
$$\mathbb{P}(D = d, C = c \mid \mathcal{D}_{\text{opt}}) = \mathbb{P}(D = d, C = c \mid \mathcal{D}_{\text{hold}}) = \mathbb{P}(D = d, C = c \mid \mathcal{D})$$

At each prompt mutation step $t \in \{1, \dots, 30\}$, the candidate prompt $\pi_t$ produces:
$$\hat{R}_{\text{opt}}(\pi_t) = \mu(\pi_t) + \epsilon_{\text{quirk}}(\pi_t), \qquad \hat{R}_{\text{hold}}(\pi_t) = \mu(\pi_t) - \delta_{\text{brittle}}(\pi_t)$$
where $\epsilon_{\text{quirk}}(\pi_t) > 0$ is spurious overfitting to $\mathcal{D}_{\text{opt}}$ quirks and $\delta_{\text{brittle}}(\pi_t) > 0$ is the generalization penalty on unseen tasks."""
    )

    code_setup = new_code_cell(
        """import numpy as np
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
print(f"Total Tasks: {len(df_bench)} | Optimization Set (60%): {len(opt_df)} | Holdout Set (40%): {len(holdout_df)}")"""
    )

    md_split = new_markdown_cell(
        """## 2. Verifying Joint Stratification Across Difficulty & Capability"""
    )

    code_split = new_code_cell(
        """comparison = pd.DataFrame({
    "Opt Set Share (%)": (opt_df["stratum"].value_counts(normalize=True) * 100).round(1),
    "Holdout Set Share (%)": (holdout_df["stratum"].value_counts(normalize=True) * 100).round(1),
    "Opt Count": opt_df["stratum"].value_counts(),
    "Holdout Count": holdout_df["stratum"].value_counts(),
}).sort_index()
comparison"""
    )

    md_sim = new_markdown_cell(
        r"""## 3. Automated Prompt Hill-Climbing Loop & `HoldoutGate`

We now simulate 30 sequential prompt mutations comparing:
1. **Ungated Hill-Climbing**: Accepts any prompt mutation that improves the Optimization Set score ($\ge +0.4\%$), blind to holdout degradation.
2. **Holdout-Gated Hill-Climbing (`HoldoutGate`)**: Evaluates candidate mutations on the unseen Holdout Set and automatically rejects overfit / reward-hacking mutations."""
    )

    code_sim = new_code_cell(
        """history_df, gate = run_prompt_hill_climbing_simulation(opt_df, holdout_df, num_steps=30, random_state=42)

# Identify the divergence point where Ungated Opt - Ungated Holdout exceeds 5 percentage points
gen_gap = history_df["ungated_opt_pass_rate"] - history_df["ungated_holdout_pass_rate"]
divergence_step = int(history_df.loc[gen_gap > 0.05, "step"].iloc[0])

print(f"Overfitting Divergence Point detected at Step {divergence_step}!")
print(f"Final Ungated Optimization Pass Rate : {history_df['ungated_opt_pass_rate'].iloc[-1]:.1%}")
print(f"Final Ungated Holdout Pass Rate      : {history_df['ungated_holdout_pass_rate'].iloc[-1]:.1%} (Overfit Collapse!)")
print(f"Final Holdout-Gated Holdout Pass Rate: {history_df['gated_holdout_pass_rate'].iloc[-1]:.1%} (Protected Generalization!)")

history_df[["step", "mutation_type", "ungated_opt_pass_rate", "ungated_holdout_pass_rate", "gated_holdout_pass_rate", "gated_accepted", "gate_reason"]].tail(12)"""
    )

    md_viz = new_markdown_cell(
        """## 4. Visualization: Goodhart's Law Divergence vs. Holdout Gate Protection"""
    )

    code_viz = new_code_cell(
        """fig, ax = plt.subplots(figsize=(11, 5.8))

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
plt.show()"""
    )

    script_code = "\n\n".join([c.source for c in [code_setup, code_split, code_sim, code_viz]])
    return script_code, [md_intro, code_setup, md_split, code_split, md_sim, code_sim, md_viz, code_viz]


def build_chapter_03() -> tuple[str, list]:
    md_intro = new_markdown_cell(
        r"""# Chapter 3: Frequentist A/B Testing & Power Analysis

When comparing a **Baseline Agent** against a **Candidate Agent** on the exact same benchmark of $N$ tasks, the outcomes are **paired** by task identity. Ignoring this pairing (by running an independent two-sample proportion $Z$-test) throws away task-level conditioning and requires **5x–10x more evaluation runs** to reach $80\%$ statistical power.

---

## 1. Mathematical Formulations

### A. Paired $2 \times 2$ Contingency Table & McNemar's Test
For each task $i \in \{1, \dots, N\}$, we observe a paired binary vector $(Y_{i,\text{base}}, Y_{i,\text{cand}}) \in \{0, 1\}^2$:

| | Candidate Pass ($1$) | Candidate Fail ($0$) | Row Total |
|---|---|---|---|
| **Baseline Pass ($1$)** | $a$ (Concordant Pass) | $b$ (Regression) | $a + b$ |
| **Baseline Fail ($0$)** | $c$ (Solved by Candidate) | $d$ (Concordant Fail) | $c + d$ |
| **Column Total** | $a + c$ | $b + d$ | $N$ |

Notice that concordant tasks ($a$ and $d$) contribute **zero information** about which agent is better—only the **discordant pairs** ($b$ and $c$) matter! **McNemar's Test** with Edwards' continuity correction tests $H_0: p_b = p_c$:
$$\chi^2_{\text{McNemar}} = \frac{(|b - c| - 1)^2}{b + c} \sim \chi^2_1$$

### B. Wilcoxon Signed-Rank Test for Skewed Continuous Telemetry
Agent token consumption and wall-clock latency follow heavy right-skewed (log-normal) distributions where parametric paired $t$-tests suffer from outlier distortion. The **Wilcoxon Signed-Rank Test** ranks the absolute paired differences $|D_i| = |X_{i,\text{cand}} - X_{i,\text{base}}|$ and sums the signed ranks $W = \sum_{i} \text{sign}(D_i) \cdot \text{rank}(|D_i|)$."""
    )

    code_setup = new_code_cell(
        """import numpy as np
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
print(f"Required tasks (Paired McNemar, rho=0.88) : {n_paired_high_corr:,} paired tasks ({n_unpaired / n_paired_high_corr:.1f}x sample reduction!)")"""
    )

    md_tests = new_markdown_cell(
        """## 2. Single-Experiment Walkthrough ($N=160$ Paired Tasks)

Let's simulate a paired benchmark evaluation on $N=160$ tasks where the Candidate Agent improves pass rate by $+5\\%$ ($65\\% \\to 70\\%$) and reduces token consumption by $\\sim 14\\%$."""
    )

    code_tests = new_code_cell(
        """exp = simulate_paired_experiment(num_tasks=160, p_baseline=0.65, p_candidate=0.70, discordant_noise=0.010, random_state=7)
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
print(f"Wilcoxon Token Test      : stat = {wilcox_res['statistic']:.1f}, p = {wilcox_res['p_value']:.4e} (Median {wilcox_res['median_baseline']:.0f} -> {wilcox_res['median_candidate']:.0f} tokens)")"""
    )

    md_mc = new_markdown_cell(
        """## 3. Monte Carlo Sample-Efficiency Comparison (1,000 Trials per Sample Size)

We now execute **1,000 Monte Carlo experiments** across sample sizes $N \\in [40, 1500]$ to compare empirical statistical power ($1 - \\beta$) between **McNemar's Paired Test** and the **Unpaired 2-Sample $Z$-Test** for detecting a $+5\\%$ pass rate improvement."""
    )

    code_mc = new_code_cell(
        """sample_sizes = [40, 80, 120, 160, 200, 250, 350, 500, 750, 1000, 1400]
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

power_df"""
    )

    script_code = "\n\n".join([c.source for c in [code_setup, code_tests, code_mc]])
    return script_code, [md_intro, code_setup, md_tests, code_tests, md_mc, code_mc]


def build_chapter_04() -> tuple[str, list]:
    md_intro = new_markdown_cell(
        r"""# Chapter 4: Multi-Knob Attribution & Multiple Regression

Agent harnesses expose multiple continuous configuration knobs that interact non-linearly:
1. `thinking_budget` ($T \in [100, 4000]$ tokens): improves complex planning initially, but exhibits **quadratic decay** at high budgets due to overthinking / reasoning loops.
2. `context_chunks` ($C \in [1, 20]$ retrieved RAG chunks): increases recall initially, then degrades due to **context distraction** ("lost in the middle").
3. `tool_timeout` ($S \in [5, 60]$ seconds): prevents premature RPC cancellations.

---

## 1. Second-Order Response Surface Model

Rather than tuning one knob at a time (which misses interaction synergies), we fit a **Second-Order Polynomial Response Surface** via Ordinary Least Squares (`statsmodels` Formula API):
$$\text{PassRate} = \beta_0 + \beta_T T + \beta_{T^2} T^2 + \beta_C C + \beta_{C^2} C^2 + \beta_{TC} (T \cdot C) + \beta_S S + \epsilon$$

To find the analytical stationary point $(T^*, C^*)$, we set the partial derivatives to zero:
$$\frac{\partial \widehat{\text{PassRate}}}{\partial T} = \beta_T + 2\beta_{T^2} T + \beta_{TC} C = 0, \qquad \frac{\partial \widehat{\text{PassRate}}}{\partial C} = \beta_C + 2\beta_{C^2} C + \beta_{TC} T = 0$$"""
    )

    code_setup = new_code_cell(
        """import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from agent_stats.ch04_multi_knob_regression import (
    extract_developer_insights,
    fit_response_surface_model,
    generate_multi_knob_dataset,
)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120

df_knobs = generate_multi_knob_dataset(n_samples=300, random_state=42)
model = fit_response_surface_model(df_knobs)
print(model.summary())"""
    )

    md_viz = new_markdown_cell(
        """## 2. 3D Response Surface & 2D Iso-Performance Contour Map"""
    )

    code_viz = new_code_cell(
        """insights = extract_developer_insights(model)
opt_t = insights["optimal_thinking_budget"]
opt_c = insights["optimal_context_chunks"]

t_grid = np.linspace(100, 4000, 60)
c_grid = np.linspace(1, 20, 60)
tt, cc = np.meshgrid(t_grid, c_grid)
grid_df = pd.DataFrame({
    "thinking_budget": tt.ravel(),
    "context_chunks": cc.ravel(),
    "tool_timeout": np.full(tt.size, 30.0),
})
zz = model.predict(grid_df).to_numpy().reshape(tt.shape)

fig = plt.figure(figsize=(15, 6.0))

# Subplot 1: 3D Response Surface
ax1 = fig.add_subplot(1, 2, 1, projection="3d")
surf = ax1.plot_surface(tt, cc, zz, cmap="viridis", alpha=0.88, edgecolor="none")
ax1.scatter([opt_t], [opt_c], [ np.max(zz) ], color="red", s=80, label="Global Optimum")
ax1.set_title("3D Response Surface: Pass Rate vs. Thinking & Context", fontsize=11.5, fontweight="bold")
ax1.set_xlabel("Thinking Budget (Tokens)")
ax1.set_ylabel("Context Chunks (k)")
ax1.set_zlabel("Predicted Pass Rate")
ax1.view_init(elev=28, azim=-125)

# Subplot 2: 2D Contour Map with Stationary Optimum & Overthinking Zone
ax2 = fig.add_subplot(1, 2, 2)
cntr = ax2.contourf(tt, cc, zz, levels=18, cmap="viridis")
cs = ax2.contour(tt, cc, zz, levels=10, colors="white", linewidths=0.8, alpha=0.7)
ax2.clabel(cs, inline=True, fontsize=8, fmt="%.2f")
plt.colorbar(cntr, ax=ax2, label="Predicted Pass Rate")

ax2.scatter([opt_t], [opt_c], color="#ff2a2a", edgecolor="white", s=140, zorder=5, marker="*", label=f"Stationary Optimum ({opt_t:,.0f} tok, {opt_c:.1f} chunks)")
ax2.axvline(opt_t, color="white", linestyle="--", alpha=0.7)
ax2.axhline(opt_c, color="white", linestyle="--", alpha=0.7)
ax2.set_title("2D Contour Map & Optimal Parameter Region (timeout=30s)", fontsize=11.5, fontweight="bold")
ax2.set_xlabel("Thinking Budget (Tokens)")
ax2.set_ylabel("Context Chunks Retrieved")
ax2.legend(loc="lower right", facecolor="#222222", labelcolor="white", framealpha=0.85)

plt.tight_layout()
plt.savefig("figures/ch04_multi_knob_response_surface.png", dpi=150, bbox_inches="tight")
plt.show()"""
    )

    md_interpret = new_markdown_cell(
        """## 3. Automated Developer Interpretation Exercises"""
    )

    code_interpret = new_code_cell(
        """print("=== AUTOMATED DEVELOPER REGRESSION INSIGHTS ===")
for line in insights["plain_english_insights"]:
    print(line)"""
    )

    script_code = "\n\n".join([c.source for c in [code_setup, code_viz, code_interpret]])
    return script_code, [md_intro, code_setup, md_viz, code_viz, md_interpret, code_interpret]


def build_chapter_05() -> tuple[str, list]:
    md_intro = new_markdown_cell(
        r"""# Chapter 5: Bayesian Sequential Testing & Early Stopping

Running a fixed horizon of $N=500$ benchmark tasks for every candidate prompt or harness tweak burns massive token budgets on doomed variants. **Bayesian Sequential Testing** updates the posterior belief after every task (or mini-batch) and stops as soon as the **Posterior Probability of Superiority** crosses a pre-configured threshold.

---

## 1. Mathematical Derivations

### A. Conjugate Beta-Binomial Updating
If a prompt's true pass rate $\theta \in [0, 1]$ has prior $\theta \sim \text{Beta}(\alpha_0, \beta_0)$ and we observe $s$ successes in $n$ Bernoulli trials, the exact closed-form posterior is:
$$\theta \mid (s, n) \sim \text{Beta}(\alpha_0 + s, \, \beta_0 + n - s)$$

### B. Posterior Probability of Superiority
Given independent posteriors $\theta_{\text{cand}} \sim \text{Beta}(\alpha_C, \beta_C)$ and $\theta_{\text{base}} \sim \text{Beta}(\alpha_B, \beta_B)$, the probability that the candidate beats the baseline is:
$$P(\theta_{\text{cand}} > \theta_{\text{base}} \mid D) = \int_0^1 f_{\text{Beta}}(x; \alpha_C, \beta_C) \cdot F_{\text{Beta}}(x; \alpha_B, \beta_B) \, dx$$
which we compute both via **exact 1D Gauss-Kronrod quadrature** (`scipy.integrate.quad`) and **Monte Carlo sampling** (`numpy`).

### C. Sequential Stopping Rules (`BetaBinomialEvaluator`)
After each step $t \ge t_{\min}$:
- **Early Accept**: $P(\theta_{\text{cand}} > \theta_{\text{base}} \mid D_t) \ge 0.95 \implies \texttt{ACCEPT}$
- **Early Abandon**: $P(\theta_{\text{cand}} > \theta_{\text{base}} \mid D_t) \le 0.10 \implies \texttt{ABANDON}$
- **Otherwise**: $\texttt{CONTINUE}$"""
    )

    code_setup = new_code_cell(
        """import numpy as np
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
print(f"P(theta_cand > theta_base | D) -> Quadrature: {p_quad:.5f} | Monte Carlo: {p_mc:.5f} (|diff| = {abs(p_quad - p_mc):.5f})")"""
    )

    md_seq = new_markdown_cell(
        """## 2. Step-by-Step Posterior Shift & Sequential Benchmark (100 Weak + 10 Strong Variants)"""
    )

    code_seq = new_code_cell(
        """# 1. Step-by-step trajectory of a Strong Candidate (p=0.77) vs Baseline (p=0.65)
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
print(f"Avg Trials per Strong Variant : {bench['strong_avg_trials']:.1f} trials (vs 500)")"""
    )

    md_viz = new_markdown_cell(
        """## 3. Visualizations: Posterior Distribution Shifts & Compute-Savings Bar Chart"""
    )

    code_viz = new_code_cell(
        r"""fig, axes = plt.subplots(1, 2, figsize=(15, 5.6))

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
plt.show()"""
    )

    script_code = "\n\n".join([c.source for c in [code_setup, code_seq, code_viz]])
    return script_code, [md_intro, code_setup, md_seq, code_seq, md_viz, code_viz]


def build_chapter_06() -> tuple[str, list]:
    md_intro = new_markdown_cell(
        r"""# Chapter 6: Hierarchical Bayesian Modeling for Edge Cases

Production agent benchmarks are often sliced into fine-grained failure categories with wildly uneven sample sizes ($N_j$ ranging from $3$ to $150$ tasks). When a rare category like `distributed_race_condition` ($N=3, S=0$) shows a $0.0\%$ raw pass rate, developers frequently panic and trigger false regression alerts.

---

## 1. Three Estimators: No Pooling, Complete Pooling, and Partial Pooling

1. **No Pooling (Raw MLE)**:
   $$\hat{\theta}_j^{\text{raw}} = \frac{S_j}{N_j}$$
   Unbiased, but has extreme variance $\frac{\theta_j(1-\theta_j)}{N_j}$ when $N_j \in \{3, 4\}$.
2. **Complete Pooling**:
   $$\hat{\theta}^{\text{pool}} = \frac{\sum_{j=1}^J S_j}{\sum_{j=1}^J N_j}$$
   Zero variance across categories, but completely ignores true differences between easy and hard slices.
3. **Partial Pooling (Hierarchical Beta-Binomial Shrinkage)**:
   We place a shared population hyperprior across all $J=8$ categories:
   $$\theta_j \sim \text{Beta}(\alpha_0, \beta_0), \qquad S_j \mid \theta_j \sim \text{Binomial}(N_j, \theta_j)$$
   Letting $\mu_0 = \frac{\alpha_0}{\alpha_0 + \beta_0}$ be the hyperprior mean and $\kappa = \alpha_0 + \beta_0$ be the prior concentration, the posterior mean for category $j$ is a **convex shrinkage combination**:
   $$\mathbb{E}[\theta_j \mid S_j, N_j] = \frac{\alpha_0 + S_j}{\alpha_0 + \beta_0 + N_j} = \underbrace{\left(\frac{\kappa}{\kappa + N_j}\right)}_{B_j \text{ (Shrinkage Weight)}} \mu_0 + \left(1 - B_j\right) \left(\frac{S_j}{N_j}\right)$$"""
    )

    code_setup = new_code_cell(
        r"""import numpy as np
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
]].round(3)"""
    )

    md_viz = new_markdown_cell(
        """## 2. Forest Plot: Raw Empirical Pass Rates vs. Hierarchically Shrunk Estimates (95% Credible Intervals)"""
    )

    code_viz = new_code_cell(
        r"""fig, ax = plt.subplots(figsize=(12, 6.2))

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
plt.show()"""
    )

    md_case = new_markdown_cell(
        """## 3. Case Study Analysis: Preventing False Regression Alarms on $N=3$ Edge Cases"""
    )

    code_case = new_code_cell(
        r"""rmse_raw = np.sqrt(np.mean((df_est["no_pooling_mean"] - df_est["true_latent_rate"]) ** 2))
rmse_shrunk = np.sqrt(np.mean((df_est["partial_pooling_mean"] - df_est["true_latent_rate"]) ** 2))

race_row = df_est.loc[df_est["category"] == "distributed_race_condition"].iloc[0]
mem_row = df_est.loc[df_est["category"] == "memory_leak"].iloc[0]

print("=== EDGE-CASE REGRESSION TRIAGE CASE STUDY ===")
print(f"1. `distributed_race_condition` (S=0/3): Raw = {race_row['no_pooling_mean']:.1%} -> Hierarchical = {race_row['partial_pooling_mean']:.1%} "
      f"(95% CrI: [{race_row['partial_pooling_ci_low']:.1%}, {race_row['partial_pooling_ci_high']:.1%}], True = {race_row['true_latent_rate']:.1%})")
print(f"2. `memory_leak` (S=1/4)               : Raw = {mem_row['no_pooling_mean']:.1%} -> Hierarchical = {mem_row['partial_pooling_mean']:.1%} "
      f"(95% CrI: [{mem_row['partial_pooling_ci_low']:.1%}, {mem_row['partial_pooling_ci_high']:.1%}], True = {mem_row['true_latent_rate']:.1%})")
print(f"3. Estimation Error (RMSE vs True Rate): No-Pooling RMSE = {rmse_raw:.3f} vs. Partial-Pooling RMSE = {rmse_shrunk:.3f} "
      f"({(1 - rmse_shrunk/rmse_raw)*100:.1f}% error reduction!)")"""
    )

    script_code = "\n\n".join([c.source for c in [code_setup, code_viz, code_case]])
    return script_code, [md_intro, code_setup, md_viz, code_viz, md_case, code_case]


def build_chapter_07() -> tuple[str, list]:
    md_intro = new_markdown_cell(
        r"""# Chapter 7: Bayesian Optimization with Gaussian Processes

Evaluating an agent harness across a full benchmark suite can cost tens of dollars and hours of wall-clock compute per configuration. Grid search over continuous parameters (`reasoning_tokens`, `context_limit`) is intractable. **Bayesian Optimization (BO)** builds a probabilistic **Gaussian Process (GP)** surrogate model of the expensive objective $f(\mathbf{x})$ and uses an **Acquisition Function** to select the most informative next configuration within **25 trials**.

---

## 1. Mathematical Formulations

### A. Gaussian Process Surrogate with Matérn $5/2$ Kernel
We model the unknown benchmark score $f(\mathbf{x}) \sim \mathcal{GP}(m(\mathbf{x}), k_{\nu=5/2}(\mathbf{x}, \mathbf{x}'))$ where the twice-differentiable **Matérn $5/2$ kernel** is:
$$k_{5/2}(r) = \sigma_f^2 \left(1 + \sqrt{5}r + \frac{5}{3}r^2\right) \exp\left(-\sqrt{5}r\right), \qquad r = \sqrt{\sum_{d=1}^D \frac{(x_d - x_d')^2}{\ell_d^2}}$$

Given $t$ noisy evaluations $\mathcal{D}_t = \{(\mathbf{x}_i, y_i)\}_{i=1}^t$, the GP provides closed-form posterior mean $\mu_t(\mathbf{x})$ and uncertainty $\sigma_t(\mathbf{x})$ at any candidate point $\mathbf{x}$.

### B. Acquisition Functions: Expected Improvement (EI) & GP-UCB
1. **Expected Improvement (EI)**:
   $$\text{EI}(\mathbf{x}) = \mathbb{E}\left[\max(0, f(\mathbf{x}) - y^+ - \xi)\right] = (\mu_t(\mathbf{x}) - y^+ - \xi)\Phi(Z) + \sigma_t(\mathbf{x})\phi(Z), \quad Z = \frac{\mu_t(\mathbf{x}) - y^+ - \xi}{\sigma_t(\mathbf{x})}$$
2. **Upper Confidence Bound (GP-UCB)**:
   $$\text{UCB}(\mathbf{x}) = \mu_t(\mathbf{x}) + \kappa \sigma_t(\mathbf{x})$$"""
    )

    code_setup = new_code_cell(
        r"""import numpy as np
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

bo_res["history_df"].tail(10)"""
    )

    md_viz = new_markdown_cell(
        """## 2. Side-by-Side Visualizations Across Iterations: GP Predicted Mean Surface vs. Acquisition Surface"""
    )

    code_viz = new_code_cell(
        r"""rr = bo_res["r_grid"]
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
plt.show()"""
    )

    script_code = "\n\n".join([c.source for c in [code_setup, code_viz]])
    return script_code, [md_intro, code_setup, md_viz, code_viz]


def build_chapter_08() -> tuple[str, list]:
    md_intro = new_markdown_cell(
        r"""# Chapter 8: Failure Trace Mining & Unsupervised Clustering

When an agent benchmark run produces hundreds of raw failure logs (`stdout`/`stderr`, tool payloads, and stack traces), manually reading every trace does not scale. By combining **TF-IDF sublinear $n$-gram vectorization**, **PCA dimensionality reduction**, and **unsupervised clustering ($k$-Means)**, we can automatically:
1. Group raw trace dumps into coherent failure mode clusters.
2. Extract top diagnostic TF-IDF keywords and the **medoid representative trace** (the trace closest to each cluster centroid $\boldsymbol{\mu}_k$).
3. Synthesize structured **Negative Constraints** ready for injection into automated system-prompt optimization loops.

---

## 1. Mathematical Pipeline

1. **Sublinear TF-IDF Vectorization**:
   $$\text{tfidf}(t, d) = \left(1 + \log \text{tf}(t, d)\right) \cdot \left(\log \frac{1 + N}{1 + \text{df}(t)} + 1\right)$$
   normalized to unit $L_2$ length $\|\mathbf{v}_d\|_2 = 1$.
2. **Medoid Extraction**:
   $$\text{medoid}(k) = \arg\min_{i \in C_k} \|\mathbf{v}_i - \boldsymbol{\mu}_k\|_2$$"""
    )

    code_setup = new_code_cell(
        r"""import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from agent_stats.ch08_trace_clustering import (
    cluster_and_diagnose_traces,
    generate_synthetic_failure_logs,
)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120

df_logs = generate_synthetic_failure_logs(num_logs=300, random_state=42)
res = cluster_and_diagnose_traces(df_logs, n_clusters=5, random_state=42)

print(f"Synthesized {len(df_logs)} agent failure traces across 5 underlying archetypes.")
print(f"Unsupervised Clustering Quality -> Silhouette Score: {res['silhouette_score']:.3f} | Adjusted Rand Index (vs ground truth): {res['adjusted_rand_index']:.3f}")

res["summary_df"][["cluster_id", "count", "dominant_archetype", "top_keywords", "medoid_log_id"]]"""
    )

    md_constraints = new_markdown_cell(
        """## 2. Auto-Diagnosis & System Prompt "Negative Constraints" Generation"""
    )

    code_constraints = new_code_cell(
        r"""print("=== AUTO-GENERATED SYSTEM PROMPT NEGATIVE CONSTRAINTS ===")
for _, row in res["summary_df"].iterrows():
    print(f"[Cluster {row['cluster_id']} | {row['dominant_archetype']} (n={row['count']})]")
    print(f"  Top TF-IDF Keywords : {row['top_keywords']}")
    print(f"  Medoid Trace ({row['medoid_log_id']}): {row['medoid_snippet']}")
    print(f"  -> Prompt Constraint: {row['negative_constraint']}")
    print("-" * 95)"""
    )

    md_viz = new_markdown_cell(
        """## 3. 2D Failure Trace Cluster Visualization (Static Matplotlib + Interactive Plotly Export)"""
    )

    code_viz = new_code_cell(
        r"""import plotly.express as px

logs_df = res["logs_df"]
summary_df = res["summary_df"]

# 1. Static High-DPI Scatter Plot with Centroid Diagnostic Labels
fig, ax = plt.subplots(figsize=(11.5, 6.2))
sns.scatterplot(
    data=logs_df,
    x="pca_x",
    y="pca_y",
    hue="cluster_label",
    style="true_archetype",
    s=75,
    alpha=0.85,
    palette="tab10",
    ax=ax,
)

for _, row in summary_df.iterrows():
    cid = row["cluster_id"]
    sub = logs_df[logs_df["cluster_id"] == cid]
    cx, cy = sub["pca_x"].mean(), sub["pca_y"].mean()
    ax.text(
        cx, cy + 0.04,
        f"Cluster {cid}: {row['dominant_archetype']}\n({row['top_keywords'].split(',')[0]})",
        ha="center", va="bottom", fontsize=8.5, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#333333", alpha=0.9),
    )

ax.set_title("2D PCA Projection of 300 Clustered Agent Failure Traces (TF-IDF + K-Means)", fontsize=12.5, fontweight="bold")
ax.set_xlabel(f"PCA Component 1 ({res['explained_variance_ratio'][0]:.1%} variance)")
ax.set_ylabel(f"PCA Component 2 ({res['explained_variance_ratio'][1]:.1%} variance)")
ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8.5)

plt.tight_layout()
plt.savefig("figures/ch08_failure_trace_clusters.png", dpi=150, bbox_inches="tight")
plt.show()

# 2. Save Interactive Plotly HTML Scatter Plot
fig_plotly = px.scatter(
    logs_df,
    x="pca_x",
    y="pca_y",
    color="cluster_label",
    symbol="true_archetype",
    hover_data=["log_id", "tool_name", "true_archetype"],
    title="Interactive 2D Clustered Agent Failure Traces (Chapter 8)",
)
fig_plotly.write_html("figures/ch08_interactive_failure_clusters.html")
print("Saved interactive Plotly scatter plot to figures/ch08_interactive_failure_clusters.html")"""
    )

    script_code = "\n\n".join([c.source for c in [code_setup, code_constraints, code_viz]])
    return script_code, [md_intro, code_setup, md_constraints, code_constraints, md_viz, code_viz]


def main() -> None:
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    chapters = [
        ("01_stochasticity_trap", build_chapter_01),
        ("02_data_hygiene_and_overfitting", build_chapter_02),
        ("03_frequentist_ab_testing", build_chapter_03),
        ("04_multi_knob_attribution", build_chapter_04),
        ("05_bayesian_sequential_testing", build_chapter_05),
        ("06_hierarchical_bayesian_modeling", build_chapter_06),
        ("07_bayesian_optimization", build_chapter_07),
        ("08_failure_trace_clustering", build_chapter_08),
    ]

    for slug, builder in chapters:
        print(f"Building and executing {slug}...")
        script_code, cells = builder()

        # Write standalone Python script in scripts/
        script_header = (
            f'"""Standalone runnable script for {slug}."""\n'
            "import matplotlib\n"
            "matplotlib.use('Agg')\n\n"
        )
        script_path = SCRIPTS_DIR / f"{slug}.py"
        script_path.write_text(script_header + script_code + "\n", encoding="utf-8")

        # Also place 02_data_hygiene_and_overfitting.py in root per Chapter 2 prompt
        if slug == "02_data_hygiene_and_overfitting":
            (ROOT_DIR / f"{slug}.py").write_text(script_header + script_code + "\n", encoding="utf-8")

        # Create and execute Jupyter Notebook in root
        nb = make_notebook(cells)
        nb_path = ROOT_DIR / f"{slug}.ipynb"
        client = NotebookClient(
            nb,
            timeout=180,
            kernel_name="python3",
            resources={"metadata": {"path": str(ROOT_DIR)}},
        )
        client.execute()
        with nb_path.open("w", encoding="utf-8") as f:
            nbformat.write(nb, f)
        print(f"  [OK] Executed & saved {nb_path.name} and scripts/{script_path.name}")


if __name__ == "__main__":
    main()
