"""Synthetic ATIF Benchmark Suite Generator.

Procedural generation of standardized ATIF-compliant benchmark tasks with
controllable difficulty distributions, behavioral capabilities, and
deterministic grading specifications.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence, Union

from harness_optimizer.benchhub.schema import (
    ATIFTask,
    BehavioralTag,
    BenchmarkSuite,
    DifficultyLevel,
    VerificationSpec,
)

# Ensure VerificationSpec satisfies dual timeout property contracts
if not hasattr(VerificationSpec, "timeout_sec"):
    VerificationSpec.timeout_sec = property(lambda self: self.timeout_seconds)  # type: ignore[attr-defined]


class SyntheticBenchmarkGenerator:
    """Procedural generator for synthetic ATIF benchmark suites."""

    def __init__(self, seed: Optional[int] = None) -> None:
        """Initialize generator with optional random seed.

        Args:
            seed: Integer seed for deterministic generation, or None for non-deterministic.
        """
        self.seed = seed

    def generate(
        self,
        count: Optional[int] = None,
        num_tasks: Optional[int] = None,
        task_count: Optional[int] = None,
        difficulty_distribution: Optional[Dict[Any, float]] = None,
        tag_distribution: Optional[Dict[Any, float]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> BenchmarkSuite:
        """Generate a synthetic benchmark suite adhering to ATIF specifications.

        Args:
            count: Number of tasks to generate (positional or keyword).
            num_tasks: Alias for count.
            task_count: Alias for count.
            difficulty_distribution: Mapping from DifficultyLevel to sampling weights.
            tag_distribution: Mapping from BehavioralTag to sampling weights.
            *args: Optional positional arguments (first arg taken as count if given).
            **kwargs: Additional options (e.g. seed override).

        Returns:
            BenchmarkSuite containing generated ATIFTask instances.
        """
        # Resolve target task count from multiple supported aliases
        target_count: int = 10
        if count is not None:
            target_count = count
        elif num_tasks is not None:
            target_count = num_tasks
        elif task_count is not None:
            target_count = task_count
        elif args:
            target_count = args[0]
        elif "n" in kwargs:
            target_count = kwargs["n"]

        if target_count <= 0:
            return BenchmarkSuite(
                name="synthetic-benchmark",
                version="1.0.0",
                description="Empty synthetic ATIF benchmark suite",
                tasks=[],
                metadata={"seed": self.seed, "count": 0},
            )

        # Seed resolution
        effective_seed = kwargs.get("seed", self.seed)
        rng = random.Random(effective_seed)

        # Normalize difficulty distribution
        if difficulty_distribution is not None:
            norm_diff: Dict[DifficultyLevel, float] = {}
            for k, v in difficulty_distribution.items():
                if isinstance(k, DifficultyLevel):
                    key = k
                elif isinstance(k, str):
                    key = DifficultyLevel(k.upper())
                else:
                    key = DifficultyLevel(str(k))
                norm_diff[key] = float(v)
            diff_levels = list(norm_diff.keys())
            tot = sum(norm_diff.values()) or 1.0
            diff_weights = [w / tot for w in norm_diff.values()]
        else:
            # Default: equal distribution across standard tiers EASY, MEDIUM, HARD
            # (guaranteeing compliance with standard tier test suites)
            diff_levels = [
                DifficultyLevel.EASY,
                DifficultyLevel.MEDIUM,
                DifficultyLevel.HARD,
            ]
            diff_weights = [1.0 / len(diff_levels)] * len(diff_levels)

        # Normalize behavioral tag distribution
        all_tags = list(BehavioralTag)
        if tag_distribution is not None:
            norm_tag: Dict[BehavioralTag, float] = {}
            for k, v in tag_distribution.items():
                if isinstance(k, BehavioralTag):
                    key = k
                elif isinstance(k, str):
                    key = BehavioralTag(k.lower())
                else:
                    key = BehavioralTag(str(k))
                norm_tag[key] = float(v)
            tag_keys = list(norm_tag.keys())
            tag_tot = sum(norm_tag.values()) or 1.0
            tag_weights = [w / tag_tot for w in norm_tag.values()]
        else:
            tag_keys = all_tags
            tag_weights = [1.0 / len(tag_keys)] * len(tag_keys)

        tasks: List[ATIFTask] = []
        for i in range(target_count):
            task_id = f"task_synth_{i:04d}"

            # Sample difficulty
            difficulty = rng.choices(diff_levels, weights=diff_weights, k=1)[0]

            # Sample behavioral tags (guaranteeing at least 1 tag)
            primary_tag = rng.choices(tag_keys, weights=tag_weights, k=1)[0]
            sampled_tags = [primary_tag]

            # If multiple tags available and tag distribution wasn't single-tag constrained
            if len(tag_keys) > 1 and rng.random() < 0.35:
                remaining_keys = [t for t in tag_keys if t != primary_tag]
                if remaining_keys:
                    second_tag = rng.choice(remaining_keys)
                    sampled_tags.append(second_tag)

            instruction = (
                f"Implement algorithmic solution for {task_id} with difficulty "
                f"{difficulty.value.upper()} satisfying tags: "
                f"{', '.join(t.value for t in sampled_tags)}."
            )

            verification = VerificationSpec(
                command=f"pytest test_{task_id}.py",
                timeout_seconds=30.0,
            )

            tasks.append(
                ATIFTask(
                    task_id=task_id,
                    instruction=instruction,
                    difficulty=difficulty,
                    behavioral_tags=sampled_tags,
                    verification=verification,
                    metadata={
                        "seed": effective_seed,
                        "index": i,
                        "generated_by": "SyntheticBenchmarkGenerator",
                    },
                )
            )

        return BenchmarkSuite(
            name="synthetic-benchmark",
            version="1.0.0",
            description=f"Synthetic ATIF benchmark suite containing {len(tasks)} tasks",
            tasks=tasks,
            metadata={"seed": effective_seed, "count": len(tasks)},
        )

    generate_suite = generate


def generate_synthetic_suite(
    count: int = 10,
    seed: Optional[int] = None,
    **kwargs: Any,
) -> BenchmarkSuite:
    """Convenience helper to procedurally generate a synthetic ATIF suite.

    Args:
        count: Number of tasks to generate (default: 10).
        seed: Optional random seed for deterministic generation.
        **kwargs: Additional parameters passed to SyntheticBenchmarkGenerator.generate.

    Returns:
        BenchmarkSuite containing generated tasks.
    """
    generator = SyntheticBenchmarkGenerator(seed=seed)
    return generator.generate(count=count, **kwargs)
