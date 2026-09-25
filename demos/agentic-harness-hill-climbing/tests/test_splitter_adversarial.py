"""Adversarial Stress Test Harness for StratifiedSplitter.

Empirically challenges:
1. Partition isolation across 50 independent Monte Carlo seeds (Zero Leakage).
2. Distribution invariance across holdout ratios (0.10, 0.20, 0.30, 0.40, 0.50)
   under both balanced and skewed distributions.
3. Edge-case ratios: rho -> 0, rho -> 1, negative values, out-of-bounds, invalid types.
4. Structural stress: all-singletons, identical strata, empty tags, tiny suites.
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple
import numpy as np
import pytest

from harness_optimizer.benchhub.schema import (
    ATIFTask,
    BehavioralTag,
    BenchmarkSuite,
    DifficultyLevel,
    VerificationSpec,
)
from harness_optimizer.benchhub.splitter import (
    StratifiedSplitter,
    jensen_shannon_divergence,
    chi_square_contingency,
)


def make_dummy_spec() -> VerificationSpec:
    return VerificationSpec(
        command="pytest -q",
        timeout_seconds=30.0,
        expected_exit_code=0,
    )


def generate_random_suite(
    n_tasks: int,
    seed: int,
    skewed: bool = False,
) -> BenchmarkSuite:
    """Generates a synthetic ATIF benchmark suite with controlled or random distributions."""
    rng = random.Random(seed)
    diffs = list(DifficultyLevel)
    tags = list(BehavioralTag)

    # If skewed, create heavily non-uniform weights
    if skewed:
        diff_weights = [0.60, 0.25, 0.10, 0.05]
        tag_probs = [0.80, 0.40, 0.15, 0.05]
    else:
        diff_weights = [0.25, 0.25, 0.25, 0.25]
        tag_probs = [0.50, 0.50, 0.50, 0.50]

    spec = make_dummy_spec()
    tasks: List[ATIFTask] = []
    for i in range(n_tasks):
        d = rng.choices(diffs, weights=diff_weights, k=1)[0]
        # Assign random subset of tags (ATIFTask requires >= 1 tag)
        assigned_tags = [t for t, p in zip(tags, tag_probs) if rng.random() < p]
        if not assigned_tags:
            assigned_tags = [rng.choice(tags)]

        tasks.append(
            ATIFTask(
                task_id=f"mc-task-{seed}-{i:04d}",
                instruction=f"Synthetic instruction {i} under seed {seed}",
                difficulty=d,
                behavioral_tags=assigned_tags,
                verification=spec,
                metadata={"seed": seed, "index": i},
            )
        )
    return BenchmarkSuite(name=f"mc-suite-{seed}", tasks=tasks)


def generate_balanced_suite(n_tasks: int = 100) -> BenchmarkSuite:
    """Generates an evenly balanced benchmark suite across all difficulty and tag pairs."""
    diffs = list(DifficultyLevel)
    tags = [BehavioralTag.TOOL_SELECTION, BehavioralTag.STATE_MUTATION]
    spec = make_dummy_spec()

    tasks: List[ATIFTask] = []
    strata_count = len(diffs) * len(tags)
    base_per_stratum = n_tasks // strata_count
    rem = n_tasks % strata_count

    idx = 0
    for d in diffs:
        for t in tags:
            c = base_per_stratum + (1 if idx < rem else 0)
            for _ in range(c):
                tasks.append(
                    ATIFTask(
                        task_id=f"bal-{idx:04d}",
                        instruction=f"Balanced task {idx}",
                        difficulty=d,
                        behavioral_tags=[t],
                        verification=spec,
                    )
                )
                idx += 1
    return BenchmarkSuite(name=f"balanced-{n_tasks}", tasks=tasks)


# =============================================================================
# CHALLENGE 1: 50 Independent Monte Carlo Seeds - Zero Leakage Stress
# =============================================================================

class TestMonteCarloIsolationStress:
    """Adversarially verifies partition isolation across 50 independent Monte Carlo seeds."""

    @pytest.mark.parametrize("seed", list(range(1000, 1050)))
    def test_partition_isolation_mc_seeds(self, seed: int):
        # Vary suite size between 20 and 250 tasks
        n_tasks = 20 + (seed % 231)
        # Alternate between balanced and skewed distributions
        skewed = (seed % 2 == 0)
        suite = generate_random_suite(n_tasks=n_tasks, seed=seed, skewed=skewed)

        # Vary holdout ratio between 0.15 and 0.45
        ratio = 0.15 + ((seed % 7) * 0.05)
        splitter = StratifiedSplitter(holdout_ratio=ratio, random_seed=seed)

        result = splitter.split(suite)
        opt_suite, hold_suite = result.optimization_suite, result.holdout_suite

        opt_ids = set(opt_suite.task_ids)
        hold_ids = set(hold_suite.task_ids)
        all_ids = set(suite.task_ids)

        # Invariant 1: Strictly disjoint (D_opt \cap D_hold = \emptyset)
        intersection = opt_ids & hold_ids
        assert len(intersection) == 0, f"LEAKAGE DETECTED on seed {seed}: {intersection}"
        assert opt_ids.isdisjoint(hold_ids), f"opt_ids.isdisjoint(hold_ids) failed on seed {seed}"

        # Invariant 2: Union completeness (D_opt \cup D_hold = D)
        assert opt_ids | hold_ids == all_ids, f"Task loss detected on seed {seed}"

        # Invariant 3: Cardinality conservation
        assert len(opt_suite) + len(hold_suite) == len(suite)
        assert len(result.optimization_tasks) == len(opt_ids)
        assert len(result.holdout_tasks) == len(hold_ids)

        # Invariant 4: Non-empty partitions
        assert len(opt_suite) >= 1
        assert len(hold_suite) >= 1

        # Invariant 5: Report flag consistency
        assert result.divergence_report.is_leak_free is True


# =============================================================================
# CHALLENGE 2: Distribution Invariance across Holdout Ratios (0.10 to 0.50)
# =============================================================================

class TestDistributionInvarianceRatios:
    """Verifies Jensen-Shannon divergence < 0.08 and Chi-Square p > 0.05 across holdout ratios."""

    @pytest.mark.parametrize("holdout_ratio", [0.10, 0.20, 0.30, 0.40, 0.50])
    @pytest.mark.parametrize("n_tasks", [100, 200])
    def test_distribution_invariance_on_balanced_suites(self, holdout_ratio: float, n_tasks: int):
        suite = generate_balanced_suite(n_tasks=n_tasks)
        splitter = StratifiedSplitter(holdout_ratio=holdout_ratio, random_seed=42)
        result = splitter.split(suite)

        report = result.divergence_report

        # Check difficulty JSD
        assert report.difficulty_jsd < 0.08, (
            f"Difficulty JSD {report.difficulty_jsd:.4f} >= 0.08 for ratio {holdout_ratio}, N={n_tasks}"
        )

        # Check per-tag JSD
        for tag_name, tag_jsd in report.tag_jsds.items():
            assert tag_jsd < 0.08, (
                f"Tag '{tag_name}' JSD {tag_jsd:.4f} >= 0.08 for ratio {holdout_ratio}, N={n_tasks}"
            )

        # Check max overall JSD
        assert report.max_jsd < 0.08, (
            f"Max JSD {report.max_jsd:.4f} >= 0.08 for ratio {holdout_ratio}, N={n_tasks}"
        )

        # Check Chi-Square p-value for difficulty
        assert report.difficulty_p_value > 0.05, (
            f"Difficulty Chi-Square p-value {report.difficulty_p_value:.4f} <= 0.05 for ratio {holdout_ratio}, N={n_tasks}"
        )

        # Check Chi-Square p-value for tags
        for tag_name, tag_p in report.tag_p_values.items():
            assert tag_p > 0.05, (
                f"Tag '{tag_name}' Chi-Square p-value {tag_p:.4f} <= 0.05 for ratio {holdout_ratio}, N={n_tasks}"
            )

        # Overall balance flag
        assert report.is_balanced is True, (
            f"Divergence report flagged is_balanced=False for ratio {holdout_ratio}, N={n_tasks}"
        )


# =============================================================================
# CHALLENGE 3: Edge-Case Ratios and Boundary Conditions
# =============================================================================

class TestEdgeCaseRatiosAndTypes:
    """Stress tests boundary ratios, extreme values, invalid types, and structural limits."""

    def test_ratio_approaching_zero(self):
        """When rho -> 0, target_holdout should clamp to at least 1 task without error."""
        suite = generate_balanced_suite(n_tasks=50)
        # Very small ratios
        for tiny_ratio in [0.001, 0.01, 0.0001, 1e-6]:
            splitter = StratifiedSplitter(holdout_ratio=tiny_ratio, random_seed=42)
            res = splitter.split(suite)
            assert len(res.holdout_tasks) == 1
            assert len(res.optimization_tasks) == len(suite) - 1
            assert res.divergence_report.is_leak_free is True

    def test_ratio_approaching_one(self):
        """When rho -> 1, target_holdout should clamp to N - 1 tasks without error."""
        suite = generate_balanced_suite(n_tasks=50)
        # Very high ratios
        for high_ratio in [0.99, 0.999, 0.9999]:
            splitter = StratifiedSplitter(holdout_ratio=high_ratio, random_seed=42)
            res = splitter.split(suite)
            assert len(res.holdout_tasks) == len(suite) - 1
            assert len(res.optimization_tasks) == 1
            assert res.divergence_report.is_leak_free is True

    @pytest.mark.parametrize("invalid_ratio", [
        0.0,
        1.0,
        -0.001,
        -1.0,
        -100.0,
        1.0001,
        2.0,
        100.0,
        float("nan"),
        float("inf"),
        float("-inf"),
    ])
    def test_invalid_numerical_ratios_raise_value_error(self, invalid_ratio: float):
        with pytest.raises(ValueError, match="Holdout ratio must be in \\(0, 1\\)"):
            StratifiedSplitter(holdout_ratio=invalid_ratio)

    @pytest.mark.parametrize("invalid_type_ratio", [
        "0.30",
        None,
        [0.30],
        {"ratio": 0.30},
    ])
    def test_invalid_type_ratios_raise_type_error(self, invalid_type_ratio: any):
        with pytest.raises(TypeError):
            StratifiedSplitter(holdout_ratio=invalid_type_ratio)

    def test_opt_ratio_parameter_equivalence(self):
        """Verify opt_ratio parameter properly converts to holdout_ratio = 1.0 - opt_ratio."""
        splitter = StratifiedSplitter(opt_ratio=0.80)
        assert math.isclose(splitter.holdout_ratio, 0.20, rel_tol=1e-9)
        assert math.isclose(splitter.opt_ratio, 0.80, rel_tol=1e-9)

        # Invalid opt_ratio
        with pytest.raises(ValueError):
            StratifiedSplitter(opt_ratio=0.0)
        with pytest.raises(ValueError):
            StratifiedSplitter(opt_ratio=1.0)
        with pytest.raises(ValueError):
            StratifiedSplitter(opt_ratio=1.5)

    def test_tiny_suites_n1_and_n0(self):
        spec = make_dummy_spec()
        splitter = StratifiedSplitter()

        # N = 0
        with pytest.raises(ValueError, match="at least 2 tasks required"):
            splitter.split(BenchmarkSuite(name="empty", tasks=[]))

        # N = 1
        t1 = ATIFTask(
            task_id="single",
            instruction="Task 1",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=spec,
        )
        with pytest.raises(ValueError, match="at least 2 tasks required"):
            splitter.split(BenchmarkSuite(name="single", tasks=[t1]))

    def test_minimal_viable_suite_n2(self):
        spec = make_dummy_spec()
        t1 = ATIFTask(
            task_id="t1",
            instruction="Task 1",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=spec,
        )
        t2 = ATIFTask(
            task_id="t2",
            instruction="Task 2",
            difficulty=DifficultyLevel.HARD,
            behavioral_tags=[BehavioralTag.STATE_MUTATION],
            verification=spec,
        )
        suite = BenchmarkSuite(name="pair", tasks=[t1, t2])
        splitter = StratifiedSplitter(holdout_ratio=0.30)
        res = splitter.split(suite)
        assert len(res.optimization_tasks) == 1
        assert len(res.holdout_tasks) == 1
        assert res.divergence_report.is_leak_free is True

    def test_all_identical_stratum(self):
        """When all tasks share the exact same composite stratum key, allocation is strictly proportional."""
        spec = make_dummy_spec()
        tasks = [
            ATIFTask(
                task_id=f"ident-{i:03d}",
                instruction=f"Identical task {i}",
                difficulty=DifficultyLevel.MEDIUM,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=spec,
            )
            for i in range(100)
        ]
        suite = BenchmarkSuite(name="identical", tasks=tasks)
        splitter = StratifiedSplitter(holdout_ratio=0.30, random_seed=42)
        res = splitter.split(suite)
        assert len(res.holdout_tasks) == 30
        assert len(res.optimization_tasks) == 70
        assert res.divergence_report.is_leak_free is True
        assert res.divergence_report.difficulty_jsd == 0.0

    def test_empty_behavioral_tags_allowed_and_defaulted(self):
        """ATIFTask schema allows empty behavioral_tags and formats composite stratum key."""
        spec = make_dummy_spec()
        task = ATIFTask(
            task_id="notag-001",
            instruction="No tag task",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[],
            verification=spec,
        )
        assert task.behavioral_tags == []
        assert task.composite_stratum_key == "EASY::"


if __name__ == "__main__":
    pytest.main(["-v", __file__])

