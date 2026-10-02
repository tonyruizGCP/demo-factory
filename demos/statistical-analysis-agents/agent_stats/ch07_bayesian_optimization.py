"""Chapter 7: Bayesian Optimization with Gaussian Processes.

Implements:
- `evaluate_harness_config(reasoning_tokens, context_limit)`: expensive synthetic
  black-box agent benchmark score with an unknown multimodal global optimum.
- Gaussian Process Surrogate Model using `sklearn.gaussian_process.GaussianProcessRegressor`
  with a Matern(nu=2.5) + WhiteKernel covariance structure.
- Acquisition Functions:
  * Expected Improvement (EI)
  * Upper Confidence Bound (GP-UCB)
- Sequential 25-Trial Bayesian Optimization Loop with snapshot history for visualizing
  GP posterior mean, uncertainty, and acquisition surfaces across iterations.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Tuple
import warnings
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.exceptions import ConvergenceWarning


REASONING_BOUNDS = (256.0, 4096.0)
CONTEXT_BOUNDS = (4.0, 64.0)  # in thousands of context tokens (4k to 64k)


def evaluate_harness_config(
    reasoning_tokens: float | np.ndarray,
    context_limit: float | np.ndarray,
    noise_std: float = 0.012,
    rng: np.random.Generator | None = None,
) -> float | np.ndarray:
    """Synthetic expensive black-box benchmark score for an agent harness configuration.

    Domain:
        reasoning_tokens in [256, 4096]
        context_limit in [4.0, 64.0] (k tokens)
    True global optimum is located near:
        (reasoning_tokens* = 2780, context_limit* = 38.5k) with true score ~ 0.884.
    Also includes a secondary local optimum near (1200, 18.0k) to test exploration vs exploitation.
    """
    r = np.asarray(reasoning_tokens, dtype=float)
    c = np.asarray(context_limit, dtype=float)

    # Normalize to [0, 1] coordinates
    rx = (r - REASONING_BOUNDS[0]) / (REASONING_BOUNDS[1] - REASONING_BOUNDS[0])
    cx = (c - CONTEXT_BOUNDS[0]) / (CONTEXT_BOUNDS[1] - CONTEXT_BOUNDS[0])

    # Primary global peak at (rx=0.657 -> ~2780 tokens, cx=0.575 -> ~38.5k context)
    global_peak = 0.44 * np.exp(
        -(((rx - 0.657) / 0.24) ** 2 + ((cx - 0.575) / 0.25) ** 2)
    )
    # Secondary local mode at (rx=0.25, cx=0.23)
    local_peak = 0.21 * np.exp(
        -(((rx - 0.25) / 0.18) ** 2 + ((cx - 0.23) / 0.20) ** 2)
    )
    # Mild ridge / interaction + quadratic penalty at extreme boundaries
    ridge = 0.08 * np.sin(2.4 * rx) * np.sin(2.2 * cx)
    base = 0.41 + global_peak + local_peak + ridge

    if noise_std > 0.0:
        if rng is None:
            rng = np.random.default_rng(42)
        base = base + rng.normal(0.0, noise_std, size=np.shape(base))

    clipped = np.clip(base, 0.10, 0.98)
    return float(clipped) if np.ndim(reasoning_tokens) == 0 else clipped


def expected_improvement(
    mu: np.ndarray, sigma: np.ndarray, y_best: float, xi: float = 0.01
) -> np.ndarray:
    """Compute Expected Improvement (EI) acquisition values."""
    sigma_safe = np.maximum(sigma, 1e-9)
    imp = mu - y_best - xi
    z = imp / sigma_safe
    ei = imp * norm.cdf(z) + sigma_safe * norm.pdf(z)
    return np.where(sigma <= 1e-9, 0.0, ei)


def upper_confidence_bound(
    mu: np.ndarray, sigma: np.ndarray, kappa: float = 2.0
) -> np.ndarray:
    """Compute Gaussian Process Upper Confidence Bound (GP-UCB) acquisition values."""
    return mu + kappa * sigma


def _normalize_coords(x_raw: np.ndarray) -> np.ndarray:
    x_norm = np.empty_like(x_raw, dtype=float)
    x_norm[:, 0] = (x_raw[:, 0] - REASONING_BOUNDS[0]) / (
        REASONING_BOUNDS[1] - REASONING_BOUNDS[0]
    )
    x_norm[:, 1] = (x_raw[:, 1] - CONTEXT_BOUNDS[0]) / (
        CONTEXT_BOUNDS[1] - CONTEXT_BOUNDS[0]
    )
    return x_norm


def run_bayesian_optimization_loop(
    n_init: int = 5,
    n_total_trials: int = 25,
    acquisition_type: Literal["EI", "UCB"] = "EI",
    snapshot_iterations: Tuple[int, ...] = (5, 12, 25),
    grid_resolution: int = 45,
    random_state: int = 42,
) -> Dict[str, object]:
    """Run a 25-trial Gaussian Process (Matern 5/2) Bayesian Optimization loop."""
    rng = np.random.default_rng(random_state)

    # Build 2D candidate grid for acquisition maximization & surface visualization
    r_grid = np.linspace(REASONING_BOUNDS[0], REASONING_BOUNDS[1], grid_resolution)
    c_grid = np.linspace(CONTEXT_BOUNDS[0], CONTEXT_BOUNDS[1], grid_resolution)
    rr, cc = np.meshgrid(r_grid, c_grid)
    grid_points = np.column_stack([rr.ravel(), cc.ravel()])
    grid_norm = _normalize_coords(grid_points)

    # True noiseless response surface for reference
    true_surface = evaluate_harness_config(rr, cc, noise_std=0.0)
    best_true_idx = int(np.argmax(true_surface))
    true_opt_r = float(grid_points[best_true_idx, 0])
    true_opt_c = float(grid_points[best_true_idx, 1])
    true_opt_val = float(true_surface.ravel()[best_true_idx])

    # Initial space-filling random design (n_init points)
    x_observed = np.column_stack(
        [
            rng.uniform(REASONING_BOUNDS[0], REASONING_BOUNDS[1], size=n_init),
            rng.uniform(CONTEXT_BOUNDS[0], CONTEXT_BOUNDS[1], size=n_init),
        ]
    )
    y_observed = np.array(
        [
            evaluate_harness_config(float(pt[0]), float(pt[1]), noise_std=0.010, rng=rng)
            for pt in x_observed
        ]
    )

    snapshots: Dict[int, Dict[str, object]] = {}
    history_rows = []

    for i in range(n_init):
        history_rows.append(
            {
                "trial": i + 1,
                "phase": "Initial Random Seed",
                "reasoning_tokens": float(x_observed[i, 0]),
                "context_limit_k": float(x_observed[i, 1]),
                "observed_score": float(y_observed[i]),
                "best_score_so_far": float(np.max(y_observed[: i + 1])),
            }
        )

    for step in range(n_init, n_total_trials + 1):
        # Fit GP with Matern 5/2 kernel on normalized coordinates
        kernel = ConstantKernel(1.0, (0.05, 10.0)) * Matern(
            length_scale=[0.25, 0.25], length_scale_bounds=(0.05, 2.0), nu=2.5
        ) + WhiteKernel(noise_level=1e-4, noise_level_bounds=(1e-6, 0.05))

        gp = GaussianProcessRegressor(
            kernel=kernel,
            n_restarts_optimizer=5,
            normalize_y=True,
            random_state=random_state,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            gp.fit(_normalize_coords(x_observed), y_observed)

        mu_grid, std_grid = gp.predict(grid_norm, return_std=True)
        y_best = float(np.max(y_observed))

        if acquisition_type == "EI":
            acq_grid = expected_improvement(mu_grid, std_grid, y_best=y_best, xi=0.008)
        else:
            acq_grid = upper_confidence_bound(mu_grid, std_grid, kappa=2.0)

        # Penalize already-sampled grid locations slightly to avoid exact duplicate queries
        dists = np.min(
            np.linalg.norm(
                grid_norm[:, None, :] - _normalize_coords(x_observed)[None, :, :],
                axis=2,
            ),
            axis=1,
        )
        acq_masked = np.where(dists < 0.02, -1e9, acq_grid)
        next_idx = int(np.argmax(acq_masked))
        next_point = grid_points[next_idx]

        if step in snapshot_iterations:
            snapshots[step] = {
                "trial": step,
                "x_observed": x_observed.copy(),
                "y_observed": y_observed.copy(),
                "mu_surface": mu_grid.reshape(rr.shape),
                "std_surface": std_grid.reshape(rr.shape),
                "acq_surface": acq_grid.reshape(rr.shape),
                "next_point": next_point.copy(),
            }

        if step < n_total_trials:
            next_val = float(
                evaluate_harness_config(
                    float(next_point[0]), float(next_point[1]), noise_std=0.010, rng=rng
                )
            )
            x_observed = np.vstack([x_observed, next_point])
            y_observed = np.append(y_observed, next_val)
            history_rows.append(
                {
                    "trial": step + 1,
                    "phase": f"BO ({acquisition_type})",
                    "reasoning_tokens": float(next_point[0]),
                    "context_limit_k": float(next_point[1]),
                    "observed_score": next_val,
                    "best_score_so_far": float(np.max(y_observed)),
                }
            )

    best_idx = int(np.argmax(y_observed))
    return {
        "history_df": pd.DataFrame(history_rows),
        "r_grid": rr,
        "c_grid": cc,
        "true_surface": true_surface,
        "true_optimum": {
            "reasoning_tokens": true_opt_r,
            "context_limit_k": true_opt_c,
            "true_score": true_opt_val,
        },
        "discovered_optimum": {
            "trial": best_idx + 1,
            "reasoning_tokens": float(x_observed[best_idx, 0]),
            "context_limit_k": float(x_observed[best_idx, 1]),
            "observed_score": float(y_observed[best_idx]),
        },
        "snapshots": snapshots,
    }
