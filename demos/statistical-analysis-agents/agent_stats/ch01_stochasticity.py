"""Chapter 1: The Stochasticity Trap (Pass@k vs. Pass^k).

Implements:
- Unbiased combinatorial estimator for Pass@k: 1 - comb(n - c, k) / comb(n, k)
- Unbiased combinatorial estimator for Pass^k: comb(c, k) / comb(n, k)
  (and empirical plugin estimator (c / n)^k)
- AgentStochasticitySimulator: simulates task-level latent success rates with
  controllable baseline capability and execution noise (logit-normal / Beta variance).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
from scipy.special import comb, expit, logit


def calculate_pass_at_k(n: int, c: int | np.ndarray, k: int) -> float | np.ndarray:
    """Calculate the unbiased estimator for Pass@k (Chen et al., 2021).

    Pass@k is the probability that at least 1 out of k independent samples
    passes the task, estimated without bias from n total trials with c successes:
        Pass@k = 1 - comb(n - c, k) / comb(n, k)

    Args:
        n: Total number of trials generated per task (n >= k).
        c: Number of successful trials (scalar or numpy array, 0 <= c <= n).
        k: Number of samples drawn (1 <= k <= n).

    Returns:
        Unbiased Pass@k estimate in [0.0, 1.0].
    """
    if k > n:
        raise ValueError(f"k ({k}) cannot exceed total trials n ({n}).")
    c_arr = np.asarray(c)
    total_combinations = comb(n, k, exact=False)
    fail_combinations = comb(n - c_arr, k, exact=False)
    result = 1.0 - (fail_combinations / total_combinations)
    return float(result) if np.ndim(c) == 0 else result


def calculate_pass_pow_k(
    n: int, c: int | np.ndarray, k: int, unbiased: bool = True
) -> float | np.ndarray:
    """Calculate Pass^k (the k-trial consistency / reliability metric).

    Pass^k (Yao et al., tau-bench) measures the probability that ALL k
    independent trials succeed on a task:
    - Unbiased combinatorial estimator (for k <= n):
          Pass^k = comb(c, k) / comb(n, k)
    - Plugin estimator:
          Pass^k = (c / n) ** k

    Args:
        n: Total number of trials generated per task.
        c: Number of successful trials (scalar or numpy array).
        k: Number of consecutive trials required to succeed.
        unbiased: If True and k <= n, use exact combinatorial estimator comb(c, k)/comb(n, k).

    Returns:
        Pass^k estimate in [0.0, 1.0].
    """
    c_arr = np.asarray(c)
    if unbiased:
        if k > n:
            raise ValueError(f"Unbiased estimator requires k ({k}) <= n ({n}).")
        total_combinations = comb(n, k, exact=False)
        all_pass_combinations = comb(c_arr, k, exact=False)
        result = all_pass_combinations / total_combinations
    else:
        result = (c_arr / float(n)) ** k
    return float(result) if np.ndim(c) == 0 else result


@dataclass
class AgentStochasticityResult:
    """Container for simulated agent evaluation runs across N tasks and n seeds."""

    name: str
    baseline_capability: float
    execution_noise: float
    task_true_probs: np.ndarray  # shape: (num_tasks,)
    trial_matrix: np.ndarray  # shape: (num_tasks, num_seeds), binary 0/1
    success_counts: np.ndarray  # shape: (num_tasks,)

    def pass_at_k_curve(self, k_values: List[int]) -> np.ndarray:
        """Compute dataset-average Pass@k for each k in k_values."""
        n = self.trial_matrix.shape[1]
        return np.array(
            [np.mean(calculate_pass_at_k(n, self.success_counts, k)) for k in k_values]
        )

    def pass_pow_k_curve(self, k_values: List[int], unbiased: bool = True) -> np.ndarray:
        """Compute dataset-average Pass^k for each k in k_values."""
        n = self.trial_matrix.shape[1]
        return np.array(
            [
                np.mean(calculate_pass_pow_k(n, self.success_counts, k, unbiased=unbiased))
                for k in k_values
            ]
        )


class AgentStochasticitySimulator:
    """Simulates an agent with task-level success distributions and run-to-run variance.

    Higher `execution_noise` pulls task-level probabilities toward 0.5 (flaky execution
    across seeds even on tasks the agent should deterministically solve or fail),
    whereas low `execution_noise` produces near-deterministic 0/1 task behavior.
    """

    def __init__(
        self,
        num_tasks: int = 200,
        num_seeds: int = 20,
        random_state: int = 42,
    ) -> None:
        self.num_tasks = num_tasks
        self.num_seeds = num_seeds
        self.rng = np.random.default_rng(random_state)
        # Fixed intrinsic task difficulty latent scores ~ N(0, 1)
        self.task_difficulty = self.rng.normal(loc=0.0, scale=1.0, size=num_tasks)

    def simulate_agent(
        self,
        name: str,
        baseline_capability: float = 0.70,
        execution_noise: float = 0.30,
        seed_offset: int = 0,
    ) -> AgentStochasticityResult:
        """Simulate N tasks over `num_seeds` repeated executions.

        Args:
            name: Agent profile label.
            baseline_capability: Expected overall pass rate (Pass@1) in (0.01, 0.99).
            execution_noise: Run-to-run stochasticity level in [0.0, 1.0].
                - 0.0 = near-deterministic execution (tasks have p_i near 0 or 1).
                - 1.0 = maximum coin-flip flakiness (tasks have p_i near baseline_capability).
            seed_offset: Offset for reproducible independent trial sampling.
        """
        clipped_cap = np.clip(baseline_capability, 0.01, 0.99)
        noise = np.clip(execution_noise, 0.01, 0.99)

        # Use Beta distribution parameterized by mean = clipped_cap and concentration
        # controlled by (1 - noise). Low noise -> U-shaped bimodal (0/1 deterministic),
        # High noise -> concentrated around clipped_cap (flaky on every task).
        # Specifically: variance of task p_i across tasks is high when deterministic,
        # and within-task Bernoulli variance p_i*(1-p_i) is high when noise is high!
        sharpness = np.interp(1.0 - noise, [0.0, 1.0], [0.25, 12.0])
        # Construct task-specific probabilities ordered by task difficulty
        # Quantile matching or logistic steepness:
        # When sharpness is high (low noise), p_i = sigmoid(sharpness * (z_0 - difficulty))
        # Solve for z_0 so that mean(p_i) == clipped_cap:
        z_grid = np.linspace(-15.0, 15.0, 2000)
        mean_probs = np.mean(
            expit(sharpness * (z_grid[:, None] - self.task_difficulty[None, :])),
            axis=1,
        )
        z_0 = float(np.interp(clipped_cap, mean_probs, z_grid))
        task_probs = expit(sharpness * (z_0 - self.task_difficulty))

        sim_rng = np.random.default_rng(self.rng.integers(1, 1_000_000) + seed_offset)
        trial_matrix = (
            sim_rng.random((self.num_tasks, self.num_seeds)) < task_probs[:, None]
        ).astype(int)
        success_counts = trial_matrix.sum(axis=1)

        return AgentStochasticityResult(
            name=name,
            baseline_capability=baseline_capability,
            execution_noise=execution_noise,
            task_true_probs=task_probs,
            trial_matrix=trial_matrix,
            success_counts=success_counts,
        )

    def consistency_delta_grid(
        self,
        capabilities: np.ndarray,
        noise_levels: np.ndarray,
        k: int = 5,
    ) -> np.ndarray:
        """Compute matrix of Consistency Delta (Pass@1 - Pass^k) over (noise, capability)."""
        delta_matrix = np.zeros((len(noise_levels), len(capabilities)))
        for i, noise in enumerate(noise_levels):
            for j, cap in enumerate(capabilities):
                res = self.simulate_agent(
                    name=f"cap_{cap:.2f}_noise_{noise:.2f}",
                    baseline_capability=float(cap),
                    execution_noise=float(noise),
                    seed_offset=i * 100 + j,
                )
                pass_1 = float(np.mean(calculate_pass_at_k(self.num_seeds, res.success_counts, 1)))
                pass_pow_k = float(
                    np.mean(calculate_pass_pow_k(self.num_seeds, res.success_counts, k))
                )
                delta_matrix[i, j] = pass_1 - pass_pow_k
        return delta_matrix
