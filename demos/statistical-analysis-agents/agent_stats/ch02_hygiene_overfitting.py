"""Chapter 2: Data Hygiene & Overfitting Prevention (Goodhart's Law & Holdout Gates).

Implements:
- Synthetic Benchmark Generator: 200 tasks with difficulty tiers (Easy, Medium, Hard)
  and capability tags (tool_selection, context_retrieval, code_execution).
- Stratified Train/Holdout Splitter (60% Optimization / 40% Holdout) preserving joint
  difficulty x capability distribution.
- HoldoutGate: evaluates candidate prompt mutations on unseen holdout data and rejects
  reward-hacking / overfit mutations.
- Automated Prompt Hill-Climbing Loop: 30 sequential mutations contrasting Ungated
  optimization (Goodhart's Law divergence) vs. Holdout-Gated optimization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


DIFFICULTY_TIERS = ["Easy", "Medium", "Hard"]
CAPABILITY_TAGS = ["tool_selection", "context_retrieval", "code_execution"]


def generate_synthetic_benchmark(
    num_tasks: int = 200, random_state: int = 42
) -> pd.DataFrame:
    """Generate 200 benchmark tasks with difficulty tiers and capability tags."""
    rng = np.random.default_rng(random_state)

    # Realistic joint weights across 3 difficulties x 3 capabilities (9 strata)
    strata = [(d, c) for d in DIFFICULTY_TIERS for c in CAPABILITY_TAGS]
    probs = np.array([0.14, 0.14, 0.12, 0.12, 0.12, 0.11, 0.09, 0.08, 0.08])
    probs = probs / probs.sum()

    # Ensure exact proportional representation with at least 10 tasks per stratum
    counts = np.round(probs * num_tasks).astype(int)
    counts[0] += num_tasks - counts.sum()

    base_pass_prob_map = {"Easy": 0.72, "Medium": 0.50, "Hard": 0.28}
    rows = []
    task_idx = 1
    for (diff, cap), count in zip(strata, counts):
        for _ in range(count):
            base_p = np.clip(
                base_pass_prob_map[diff] + rng.normal(0.0, 0.08), 0.05, 0.92
            )
            rows.append(
                {
                    "task_id": f"TASK-{task_idx:03d}",
                    "difficulty": diff,
                    "capability": cap,
                    "stratum": f"{diff}__{cap}",
                    "base_pass_prob": float(base_p),
                    "quirk_sensitivity": float(rng.uniform(0.4, 1.0)),
                }
            )
            task_idx += 1

    df = pd.DataFrame(rows)
    return df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)


def stratified_benchmark_split(
    df: pd.DataFrame,
    holdout_fraction: float = 0.40,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split benchmark into Optimization (60%) and Holdout (40%) preserving joint strata."""
    opt_df, holdout_df = train_test_split(
        df,
        test_size=holdout_fraction,
        stratify=df["stratum"],
        random_state=random_state,
    )
    return opt_df.reset_index(drop=True), holdout_df.reset_index(drop=True)


@dataclass
class PromptMutation:
    """Represents a candidate prompt edit in an automated prompt optimizer."""

    step: int
    mutation_type: str  # "genuine_capability" | "reward_hacking" | "neutral_noise"
    description: str
    true_generalization_delta: float  # Real improvement on both Opt and Holdout
    opt_quirk_exploit_delta: float  # Overfit gain ONLY on Optimization set
    holdout_penalty_delta: float  # Brittle side-effect penalty on unseen Holdout set


class HoldoutGate:
    """Verification gate that guards against Goodhart's Law / prompt overfitting.

    A mutation is accepted ONLY if:
    1. It improves the Optimization set score by at least `min_opt_gain`, AND
    2. Its Holdout set pass rate does not regress below `current_holdout - max_holdout_drop`
       AND the generalization gap `(opt_score - holdout_score)` stays bounded.
    """

    def __init__(
        self,
        min_opt_gain: float = 0.005,
        min_holdout_gain: float = -0.002,
        max_generalization_gap: float = 0.06,
    ) -> None:
        self.min_opt_gain = min_opt_gain
        self.min_holdout_gain = min_holdout_gain
        self.max_generalization_gap = max_generalization_gap

    def evaluate_candidate(
        self,
        current_opt_score: float,
        current_holdout_score: float,
        candidate_opt_score: float,
        candidate_holdout_score: float,
    ) -> Tuple[bool, str]:
        """Return (accepted, reason) for a candidate prompt mutation."""
        opt_delta = candidate_opt_score - current_opt_score
        holdout_delta = candidate_holdout_score - current_holdout_score
        gen_gap = candidate_opt_score - candidate_holdout_score

        if opt_delta < self.min_opt_gain:
            return False, f"Rejected (Opt delta {opt_delta:+.2%} < {self.min_opt_gain:+.2%})"
        if holdout_delta < self.min_holdout_gain:
            return (
                False,
                f"Rejected by Holdout Gate (Holdout regressed {holdout_delta:+.2%})",
            )
        if gen_gap > self.max_generalization_gap:
            return (
                False,
                f"Rejected by Holdout Gate (Gen gap {gen_gap:.2%} > {self.max_generalization_gap:.2%})",
            )
        return (
            True,
            f"Accepted (Opt {opt_delta:+.2%}, Holdout {holdout_delta:+.2%})",
        )


def run_prompt_hill_climbing_simulation(
    opt_df: pd.DataFrame,
    holdout_df: pd.DataFrame,
    num_steps: int = 30,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, HoldoutGate]:
    """Simulate 30 sequential prompt mutations under Ungated vs Holdout-Gated hill climbing."""
    rng = np.random.default_rng(random_state)
    gate = HoldoutGate(
        min_opt_gain=0.004,
        min_holdout_gain=0.000,
        max_generalization_gap=0.055,
    )

    # Initial scores (Step 0)
    base_opt = float(opt_df["base_pass_prob"].mean())
    base_holdout = float(holdout_df["base_pass_prob"].mean())

    ungated_opt = base_opt
    ungated_holdout = base_holdout

    gated_opt = base_opt
    gated_holdout = base_holdout

    history = [
        {
            "step": 0,
            "mutation_type": "baseline",
            "description": "Initial System Prompt v0",
            "ungated_opt_pass_rate": ungated_opt,
            "ungated_holdout_pass_rate": ungated_holdout,
            "ungated_accepted": True,
            "gated_opt_pass_rate": gated_opt,
            "gated_holdout_pass_rate": gated_holdout,
            "gated_accepted": True,
            "gate_reason": "Baseline initialization",
        }
    ]

    for step in range(1, num_steps + 1):
        # Early steps (1..10) have more genuine capability gains;
        # Later steps (11..30) are dominated by reward-hacking / benchmark memorization
        if step <= 10:
            m_type = rng.choice(
                ["genuine_capability", "reward_hacking", "neutral_noise"],
                p=[0.55, 0.25, 0.20],
            )
        else:
            m_type = rng.choice(
                ["genuine_capability", "reward_hacking", "neutral_noise"],
                p=[0.20, 0.65, 0.15],
            )

        if m_type == "genuine_capability":
            true_delta = float(rng.uniform(0.010, 0.024))
            quirk_delta = float(rng.uniform(-0.002, 0.004))
            holdout_pen = float(rng.uniform(-0.002, 0.003))
            desc = f"Step {step:02d}: Structured tool schema & error-recovery guidance"
        elif m_type == "reward_hacking":
            true_delta = float(rng.uniform(-0.004, 0.003))
            quirk_delta = float(rng.uniform(0.012, 0.028))
            holdout_pen = float(rng.uniform(-0.018, -0.006))
            desc = f"Step {step:02d}: Hardcoded regex/few-shot workaround for Opt task IDs"
        else:
            true_delta = float(rng.uniform(-0.008, 0.003))
            quirk_delta = float(rng.uniform(-0.005, 0.003))
            holdout_pen = float(rng.uniform(-0.005, 0.003))
            desc = f"Step {step:02d}: Cosmetic phrasing rewording"

        # 1. Ungated optimizer only looks at Optimization set score!
        cand_ungated_opt = np.clip(ungated_opt + true_delta + quirk_delta, 0.0, 0.98)
        cand_ungated_holdout = np.clip(
            ungated_holdout + true_delta + holdout_pen, 0.0, 0.98
        )
        ungated_accept = (cand_ungated_opt - ungated_opt) >= 0.004
        if ungated_accept:
            ungated_opt = float(cand_ungated_opt)
            ungated_holdout = float(cand_ungated_holdout)

        # 2. Holdout-Gated optimizer verifies candidate on HoldoutGate
        cand_gated_opt = np.clip(gated_opt + true_delta + quirk_delta, 0.0, 0.98)
        cand_gated_holdout = np.clip(
            gated_holdout + true_delta + holdout_pen, 0.0, 0.98
        )
        gated_accept, reason = gate.evaluate_candidate(
            gated_opt, gated_holdout, float(cand_gated_opt), float(cand_gated_holdout)
        )
        if gated_accept:
            gated_opt = float(cand_gated_opt)
            gated_holdout = float(cand_gated_holdout)

        history.append(
            {
                "step": step,
                "mutation_type": str(m_type),
                "description": desc,
                "ungated_opt_pass_rate": ungated_opt,
                "ungated_holdout_pass_rate": ungated_holdout,
                "ungated_accepted": bool(ungated_accept),
                "gated_opt_pass_rate": gated_opt,
                "gated_holdout_pass_rate": gated_holdout,
                "gated_accepted": bool(gated_accept),
                "gate_reason": reason,
            }
        )

    return pd.DataFrame(history), gate
