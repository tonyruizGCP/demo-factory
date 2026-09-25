"""Comprehensive Unit Test Suite for BenchHub Schemas, Loaders, and Stratified Partitioner.

Verifies:
1. ATIF schema contracts, validation bounds, and normalization.
2. Robust loader ingestion across JSON, YAML, multi-doc YAML, and directory trees.
3. Duplicate task_id detection under RAISE, OVERWRITE, and IGNORE policies.
4. Error handling for malformed syntax and invalid taxonomy tags under strict and permissive modes.
5. Serialization and lossless round-tripping.
6. Zero-leakage partitioning, split ratios, and statistical balance (JSD < 0.05, Chi-Square p > 0.05).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pytest
import yaml

from harness_optimizer.benchhub.schema import (
    ATIFTask,
    BehavioralTag,
    BenchmarkSuite,
    DifficultyLevel,
    VerificationSpec,
)
from harness_optimizer.benchhub.loader import (
    BenchHubError,
    DuplicatePolicy,
    DuplicateTaskError,
    SuiteLoadError,
    SuiteValidationError,
    load_suite,
    load_suite_from_dict,
    load_suite_from_directory,
    load_suite_from_file,
    load_suite_from_json_string,
    load_suite_from_list,
    load_suite_from_yaml_string,
    save_suite,
    save_suite_to_file,
    suite_to_dict,
    suite_to_json,
    suite_to_yaml,
)
from harness_optimizer.benchhub.splitter import StratifiedSplitter


# =============================================================================
# Statistical Helper Functions (Hermetic, Zero Scipy Dependency)
# =============================================================================

def jensen_shannon_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """Compute Jensen-Shannon Divergence between two discrete distributions."""
    p_norm = np.asarray(p, dtype=float) / np.sum(p)
    q_norm = np.asarray(q, dtype=float) / np.sum(q)
    m = 0.5 * (p_norm + q_norm)

    def kl(a: np.ndarray, b: np.ndarray) -> float:
        mask = (a > 0) & (b > 0)
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))

    js = 0.5 * kl(p_norm, m) + 0.5 * kl(q_norm, m)
    return float(max(0.0, js))


def chi2_survival(x: float, df: int) -> float:
    """Compute Chi-Square distribution survival function (p-value) without scipy."""
    if x <= 0:
        return 1.0
    if df == 1:
        return math.erfc(math.sqrt(x / 2.0))

    s = df / 2.0
    z = x / 2.0
    # Regularized lower incomplete gamma via series expansion: P(s, z)
    term = 1.0 / s
    total = term
    for k in range(1, 100):
        term *= z / (s + k)
        total += term
        if term < 1e-12 * total:
            break
    lower_gamma = total * math.exp(s * math.log(z) - z - math.lgamma(s))
    return float(max(0.0, min(1.0, 1.0 - lower_gamma)))


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture
def sample_verification_spec() -> VerificationSpec:
    return VerificationSpec(
        command="pytest tests/test_patch.py",
        script=None,
        timeout_seconds=45.0,
        expected_exit_code=0,
        artifact_paths=["dist/build.tar.gz"],
        environment_variables={"ENV": "test"},
    )


@pytest.fixture
def sample_task(sample_verification_spec: VerificationSpec) -> ATIFTask:
    return ATIFTask(
        task_id="task-001",
        instruction="Fix the null pointer exception in query parser.",
        difficulty=DifficultyLevel.MEDIUM,
        behavioral_tags=[BehavioralTag.TOOL_SELECTION, BehavioralTag.STATE_MUTATION],
        verification=sample_verification_spec,
        metadata={"repo": "test/repo"},
    )


@pytest.fixture
def small_suite(sample_verification_spec: VerificationSpec) -> BenchmarkSuite:
    tasks = [
        ATIFTask(
            task_id="t1",
            instruction="Implement feature A",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=sample_verification_spec,
        ),
        ATIFTask(
            task_id="t2",
            instruction="Fix memory leak in buffer",
            difficulty=DifficultyLevel.MEDIUM,
            behavioral_tags=[BehavioralTag.STATE_MUTATION],
            verification=sample_verification_spec,
        ),
        ATIFTask(
            task_id="t3",
            instruction="Refactor auth middleware",
            difficulty=DifficultyLevel.HARD,
            behavioral_tags=[BehavioralTag.MULTI_STEP_RETRIEVAL, BehavioralTag.CONSTRAINT_ADHERENCE],
            verification=sample_verification_spec,
        ),
    ]
    return BenchmarkSuite(name="small-suite", tasks=tasks)


@pytest.fixture
def balanced_100_suite(sample_verification_spec: VerificationSpec) -> BenchmarkSuite:
    """Generate a 100-task balanced suite with known difficulty & tag proportions."""
    diffs = [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD, DifficultyLevel.EXPERT]
    tasks = []
    idx = 0
    # Create 8 balanced strata with 12 or 13 tasks each (total 100)
    for d in diffs:
        for t in [BehavioralTag.TOOL_SELECTION, BehavioralTag.STATE_MUTATION]:
            count = 13 if len(tasks) < 50 else 12
            for _ in range(count):
                tasks.append(
                    ATIFTask(
                        task_id=f"task-{idx:03d}",
                        instruction=f"Instruction for benchmark task {idx}",
                        difficulty=d,
                        behavioral_tags=[t],
                        verification=sample_verification_spec,
                    )
                )
                idx += 1
    return BenchmarkSuite(name="balanced-100-suite", tasks=tasks[:100])


# =============================================================================
# Suite 1: Schema & Core Contracts Validation
# =============================================================================

class TestEnumsAndTaxonomy:
    def test_behavioral_tag_values_and_casing(self):
        assert BehavioralTag.TOOL_SELECTION.value == "tool_selection"
        assert BehavioralTag.MULTI_STEP_RETRIEVAL.value == "multi_step_retrieval"
        assert BehavioralTag.STATE_MUTATION.value == "state_mutation"
        assert BehavioralTag.CONSTRAINT_ADHERENCE.value == "constraint_adherence"

        # Case and hyphen normalization
        assert BehavioralTag("tool-selection") == BehavioralTag.TOOL_SELECTION
        assert BehavioralTag("STATE_MUTATION") == BehavioralTag.STATE_MUTATION
        assert BehavioralTag("Multi-Step-Retrieval") == BehavioralTag.MULTI_STEP_RETRIEVAL

    def test_behavioral_tag_invalid_raises(self):
        with pytest.raises(ValueError):
            BehavioralTag("invalid_random_tag")

    def test_difficulty_level_values_and_ordering(self):
        assert DifficultyLevel.EASY < DifficultyLevel.MEDIUM < DifficultyLevel.HARD < DifficultyLevel.EXPERT
        assert DifficultyLevel.EASY.rank == 1
        assert DifficultyLevel.EXPERT.rank == 4

        # Normalization
        assert DifficultyLevel("easy") == DifficultyLevel.EASY
        assert DifficultyLevel("hard") == DifficultyLevel.HARD

    def test_difficulty_level_invalid_raises(self):
        with pytest.raises(ValueError):
            DifficultyLevel("IMPOSSIBLE")


class TestVerificationSpec:
    def test_verification_spec_defaults(self):
        v = VerificationSpec(command="pytest")
        assert v.command == "pytest"
        assert v.script is None
        assert v.timeout_seconds == 60.0
        assert v.expected_exit_code == 0
        assert v.artifact_paths == []
        assert v.environment_variables == {}

    def test_verification_spec_empty_command_raises(self):
        with pytest.raises(ValueError, match="empty or whitespace"):
            VerificationSpec(command="   ")

    def test_verification_spec_invalid_timeout_raises(self):
        with pytest.raises(ValueError):
            VerificationSpec(command="pytest", timeout_seconds=0.0)
        with pytest.raises(ValueError):
            VerificationSpec(command="pytest", timeout_seconds=4000.0)


class TestATIFTask:
    def test_atif_task_creation_and_properties(self, sample_task: ATIFTask):
        assert sample_task.task_id == "task-001"
        assert sample_task.difficulty == DifficultyLevel.MEDIUM
        assert sample_task.has_tag(BehavioralTag.TOOL_SELECTION)
        assert sample_task.has_tag("state_mutation")
        assert not sample_task.has_tag(BehavioralTag.CONSTRAINT_ADHERENCE)
        assert sample_task.composite_stratum_key == "MEDIUM::state_mutation+tool_selection"

    def test_atif_task_tag_deduplication(self, sample_verification_spec: VerificationSpec):
        task = ATIFTask(
            task_id="t-dup",
            instruction="Deduplicate tags",
            difficulty=DifficultyLevel.HARD,
            behavioral_tags=[
                BehavioralTag.TOOL_SELECTION,
                BehavioralTag.TOOL_SELECTION,
                BehavioralTag.STATE_MUTATION,
            ],
            verification=sample_verification_spec,
        )
        assert len(task.behavioral_tags) == 2
        assert task.behavioral_tags == [BehavioralTag.STATE_MUTATION, BehavioralTag.TOOL_SELECTION]

    def test_atif_task_stratum_key_order_invariance(self, sample_verification_spec: VerificationSpec):
        t1 = ATIFTask(
            task_id="t1",
            instruction="Test 1",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION, BehavioralTag.STATE_MUTATION],
            verification=sample_verification_spec,
        )
        t2 = ATIFTask(
            task_id="t2",
            instruction="Test 2",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.STATE_MUTATION, BehavioralTag.TOOL_SELECTION],
            verification=sample_verification_spec,
        )
        assert t1.composite_stratum_key == t2.composite_stratum_key

    def test_atif_task_hash_and_equality(self, sample_verification_spec: VerificationSpec):
        t1 = ATIFTask(
            task_id="t1",
            instruction="Inst 1",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=sample_verification_spec,
        )
        t2 = ATIFTask(
            task_id="t1",
            instruction="Inst 2 (different)",
            difficulty=DifficultyLevel.HARD,
            behavioral_tags=[BehavioralTag.STATE_MUTATION],
            verification=sample_verification_spec,
        )
        assert t1 == t2
        assert hash(t1) == hash(t2)
        assert len({t1, t2}) == 1

    def test_atif_task_empty_fields_raise(self, sample_verification_spec: VerificationSpec):
        with pytest.raises(ValueError):
            ATIFTask(
                task_id="   ",
                instruction="Valid instruction",
                difficulty=DifficultyLevel.EASY,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=sample_verification_spec,
            )
        with pytest.raises(ValueError):
            ATIFTask(
                task_id="valid-id",
                instruction="   ",
                difficulty=DifficultyLevel.EASY,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=sample_verification_spec,
            )


class TestBenchmarkSuite:
    def test_benchmark_suite_creation_and_indexing(self, small_suite: BenchmarkSuite):
        assert len(small_suite) == 3
        assert small_suite[0].task_id == "t1"
        assert small_suite["t2"].instruction == "Fix memory leak in buffer"
        assert "t3" in small_suite
        assert "t99" not in small_suite

    def test_benchmark_suite_duplicate_task_id_raises(self, sample_task: ATIFTask):
        with pytest.raises(ValueError, match="Duplicate task_id"):
            BenchmarkSuite(name="dup-suite", tasks=[sample_task, sample_task])

    def test_benchmark_suite_distributions_and_queries(self, small_suite: BenchmarkSuite):
        diff_dist = small_suite.difficulty_distribution
        assert diff_dist[DifficultyLevel.EASY] == 1
        assert diff_dist[DifficultyLevel.MEDIUM] == 1
        assert diff_dist[DifficultyLevel.HARD] == 1
        assert diff_dist[DifficultyLevel.EXPERT] == 0

        tag_dist = small_suite.tag_distribution
        assert tag_dist[BehavioralTag.TOOL_SELECTION] == 1
        assert tag_dist[BehavioralTag.MULTI_STEP_RETRIEVAL] == 1

        easy_tasks = small_suite.filter_by_difficulty(DifficultyLevel.EASY)
        assert len(easy_tasks) == 1
        assert easy_tasks[0].task_id == "t1"

        strata = small_suite.get_strata()
        assert len(strata) == 3


# =============================================================================
# Suite 2: Loader Ingestion & File Formats
# =============================================================================

class TestLoaderFileIngestion:
    def test_load_single_task_json(self, tmp_path: Path):
        file_path = tmp_path / "single_task.json"
        data = {
            "task_id": "task-json-1",
            "instruction": "Run tests",
            "difficulty": "EASY",
            "behavioral_tags": ["tool_selection"],
            "verification": {"command": "pytest"},
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        suite = load_suite_from_file(file_path)
        assert len(suite) == 1
        assert suite[0].task_id == "task-json-1"

    def test_load_task_list_json(self, tmp_path: Path):
        file_path = tmp_path / "task_list.json"
        data = [
            {
                "task_id": "list-1",
                "instruction": "Fix item 1",
                "difficulty": "MEDIUM",
                "behavioral_tags": ["state_mutation"],
                "verification": {"command": "make test"},
            },
            {
                "task_id": "list-2",
                "instruction": "Fix item 2",
                "difficulty": "HARD",
                "behavioral_tags": ["multi_step_retrieval"],
                "verification": {"command": "make test"},
            },
        ]
        file_path.write_text(json.dumps(data), encoding="utf-8")

        suite = load_suite_from_file(file_path)
        assert len(suite) == 2
        assert suite.task_ids == ["list-1", "list-2"]

    def test_load_full_suite_json(self, tmp_path: Path):
        file_path = tmp_path / "full_suite.json"
        data = {
            "name": "custom-json-suite",
            "version": "2.1.0",
            "description": "Full suite test",
            "tasks": [
                {
                    "task_id": "suite-1",
                    "instruction": "Task 1",
                    "difficulty": "EASY",
                    "behavioral_tags": ["tool_selection"],
                    "verification": {"command": "pytest"},
                }
            ],
        }
        file_path.write_text(json.dumps(data), encoding="utf-8")

        suite = load_suite_from_file(file_path)
        assert suite.name == "custom-json-suite"
        assert suite.version == "2.1.0"
        assert len(suite) == 1

    def test_load_multi_document_yaml(self, tmp_path: Path):
        file_path = tmp_path / "multi_doc.yaml"
        yaml_content = """
task_id: yaml-doc-1
instruction: First task
difficulty: EASY
behavioral_tags: [tool_selection]
verification:
  command: pytest
---
task_id: yaml-doc-2
instruction: Second task
difficulty: HARD
behavioral_tags: [state_mutation, constraint_adherence]
verification:
  command: pytest tests/test_doc2.py
"""
        file_path.write_text(yaml_content, encoding="utf-8")

        suite = load_suite_from_file(file_path)
        assert len(suite) == 2
        assert suite.task_ids == ["yaml-doc-1", "yaml-doc-2"]
        assert suite["yaml-doc-2"].difficulty == DifficultyLevel.HARD


class TestLoaderDirectoryIngestion:
    def test_load_directory_mixed_files_recursive(self, tmp_path: Path):
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()

        # Task 1 in JSON
        t1_path = tmp_path / "task1.json"
        t1_path.write_text(
            json.dumps({
                "task_id": "dir-1",
                "instruction": "Instruction 1",
                "difficulty": "EASY",
                "behavioral_tags": ["tool_selection"],
                "verification": {"command": "pytest"},
            })
        )

        # Task 2 in YAML (in subdirectory)
        t2_path = sub_dir / "task2.yaml"
        t2_path.write_text(
            """
task_id: dir-2
instruction: Instruction 2
difficulty: MEDIUM
behavioral_tags: [state_mutation]
verification:
  command: pytest
"""
        )

        suite = load_suite_from_directory(tmp_path, recursive=True)
        assert len(suite) == 2
        assert "dir-1" in suite
        assert "dir-2" in suite

    def test_load_directory_pattern_filter(self, tmp_path: Path):
        t1 = tmp_path / "test.task.json"
        t1.write_text(
            json.dumps({
                "task_id": "p-1",
                "instruction": "Pass",
                "difficulty": "EASY",
                "behavioral_tags": ["tool_selection"],
                "verification": {"command": "pytest"},
            })
        )
        t2 = tmp_path / "test.other.json"
        t2.write_text(
            json.dumps({
                "task_id": "p-2",
                "instruction": "Ignore",
                "difficulty": "EASY",
                "behavioral_tags": ["tool_selection"],
                "verification": {"command": "pytest"},
            })
        )

        suite = load_suite_from_directory(tmp_path, pattern="*.task.json")
        assert len(suite) == 1
        assert suite[0].task_id == "p-1"


class TestLoaderCollisionAndErrors:
    def test_duplicate_task_id_raise_policy(self, tmp_path: Path):
        f1 = tmp_path / "f1.json"
        f2 = tmp_path / "f2.json"
        task_data = {
            "task_id": "collision-task",
            "instruction": "Test collision",
            "difficulty": "EASY",
            "behavioral_tags": ["tool_selection"],
            "verification": {"command": "pytest"},
        }
        f1.write_text(json.dumps(task_data))
        f2.write_text(json.dumps(task_data))

        with pytest.raises(DuplicateTaskError):
            load_suite_from_directory(tmp_path, on_duplicate="raise")

    def test_duplicate_task_id_overwrite_and_ignore_policies(self, tmp_path: Path):
        f1 = tmp_path / "f1.json"
        f2 = tmp_path / "f2.json"
        f1.write_text(
            json.dumps({
                "task_id": "same-id",
                "instruction": "Version 1",
                "difficulty": "EASY",
                "behavioral_tags": ["tool_selection"],
                "verification": {"command": "pytest"},
            })
        )
        f2.write_text(
            json.dumps({
                "task_id": "same-id",
                "instruction": "Version 2",
                "difficulty": "HARD",
                "behavioral_tags": ["tool_selection"],
                "verification": {"command": "pytest"},
            })
        )

        # Overwrite policy retains latest
        suite_over = load_suite_from_directory(tmp_path, on_duplicate="overwrite")
        assert len(suite_over) == 1
        assert suite_over["same-id"].instruction == "Version 2"

        # Ignore policy retains first
        suite_ign = load_suite_from_directory(tmp_path, on_duplicate="ignore")
        assert len(suite_ign) == 1
        assert suite_ign["same-id"].instruction == "Version 1"

    def test_corrupted_json_raises_load_error(self, tmp_path: Path):
        bad_json = tmp_path / "broken.json"
        bad_json.write_text("{ unquoted_key: 'value' invalid }")

        with pytest.raises(SuiteLoadError, match="Malformed JSON syntax"):
            load_suite_from_file(bad_json)

    def test_corrupted_yaml_raises_load_error(self, tmp_path: Path):
        bad_yaml = tmp_path / "broken.yaml"
        bad_yaml.write_text(":\n  - invalid : : : yaml")

        with pytest.raises(SuiteLoadError, match="Malformed YAML syntax"):
            load_suite_from_file(bad_yaml)

    def test_nonexistent_file_raises_load_error(self):
        with pytest.raises(SuiteLoadError, match="File not found"):
            load_suite_from_file("non_existent_file_12345.json")

    def test_permissive_mode_skips_invalid_tasks(self, tmp_path: Path):
        good = {
            "task_id": "good-1",
            "instruction": "Good task",
            "difficulty": "EASY",
            "behavioral_tags": ["tool_selection"],
            "verification": {"command": "pytest"},
        }
        bad = {
            "task_id": "bad-1",
            # missing instruction
            "difficulty": "NON_EXISTENT_DIFF",
            "behavioral_tags": ["unknown_tag"],
            "verification": {"command": "pytest"},
        }
        f = tmp_path / "mixed.json"
        f.write_text(json.dumps([good, bad]))

        # In strict mode, raises
        with pytest.raises(SuiteValidationError):
            load_suite_from_file(f, strict=True)

        # In permissive mode, returns valid task
        suite = load_suite_from_file(f, strict=False)
        assert len(suite) == 1
        assert suite[0].task_id == "good-1"


class TestLoaderSerialization:
    def test_json_and_yaml_roundtrip(self, small_suite: BenchmarkSuite, tmp_path: Path):
        json_path = tmp_path / "sub" / "roundtrip.json"
        yaml_path = tmp_path / "sub" / "roundtrip.yaml"

        save_suite(small_suite, json_path, format="json")
        save_suite(small_suite, yaml_path, format="yaml")

        assert json_path.exists()
        assert yaml_path.exists()

        reloaded_json = load_suite_from_file(json_path)
        reloaded_yaml = load_suite_from_file(yaml_path)

        assert len(reloaded_json) == len(small_suite)
        assert len(reloaded_yaml) == len(small_suite)
        assert reloaded_json.task_ids == small_suite.task_ids
        assert reloaded_yaml.task_ids == small_suite.task_ids

    def test_string_serialization_helpers(self, small_suite: BenchmarkSuite):
        json_str = suite_to_json(small_suite)
        yaml_str = suite_to_yaml(small_suite)

        suite_from_json = load_suite_from_json_string(json_str)
        suite_from_yaml = load_suite_from_yaml_string(yaml_str)

        assert len(suite_from_json) == len(small_suite)
        assert len(suite_from_yaml) == len(small_suite)


# =============================================================================
# Suite 3: Stratified Partitioner Invariants & Statistical Tests
# =============================================================================

class TestSplitterInvariantsAndRatios:
    def test_zero_leakage_isolation(self, balanced_100_suite: BenchmarkSuite):
        splitter = StratifiedSplitter(holdout_ratio=0.30, random_seed=42)
        opt_suite, hold_suite = splitter.split(balanced_100_suite)

        opt_ids = set(opt_suite.task_ids)
        hold_ids = set(hold_suite.task_ids)

        # Strict isolation invariants
        assert opt_ids.isdisjoint(hold_ids), "Optimization and Holdout sets must be strictly disjoint!"
        assert len(opt_ids & hold_ids) == 0
        assert opt_ids | hold_ids == set(balanced_100_suite.task_ids)
        assert len(opt_suite) + len(hold_suite) == len(balanced_100_suite)

    def test_split_proportions(self, balanced_100_suite: BenchmarkSuite):
        splitter = StratifiedSplitter(holdout_ratio=0.30, random_seed=42)
        opt_suite, hold_suite = splitter.split(balanced_100_suite)

        # Proportions should be approximately 70 / 30
        assert 65 <= len(opt_suite) <= 75
        assert 25 <= len(hold_suite) <= 35

    def test_determinism_with_seed(self, balanced_100_suite: BenchmarkSuite):
        splitter1 = StratifiedSplitter(holdout_ratio=0.30, random_seed=123)
        splitter2 = StratifiedSplitter(holdout_ratio=0.30, random_seed=123)
        splitter3 = StratifiedSplitter(holdout_ratio=0.30, random_seed=999)

        opt1, hold1 = splitter1.split(balanced_100_suite)
        opt2, hold2 = splitter2.split(balanced_100_suite)
        opt3, hold3 = splitter3.split(balanced_100_suite)

        assert opt1.task_ids == opt2.task_ids
        assert hold1.task_ids == hold2.task_ids
        # Different seeds should produce distinct partitions
        assert opt1.task_ids != opt3.task_ids

    def test_invalid_ratios_raise(self):
        with pytest.raises(ValueError):
            StratifiedSplitter(holdout_ratio=0.0)
        with pytest.raises(ValueError):
            StratifiedSplitter(holdout_ratio=1.0)
        with pytest.raises(ValueError):
            StratifiedSplitter(holdout_ratio=-0.2)


class TestSplitterStatisticalDivergence:
    def test_marginal_proportions_and_jsd(self, balanced_100_suite: BenchmarkSuite):
        splitter = StratifiedSplitter(holdout_ratio=0.30, random_seed=42)
        opt_suite, hold_suite = splitter.split(balanced_100_suite)

        diffs = [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD, DifficultyLevel.EXPERT]
        opt_diff_counts = [opt_suite.difficulty_distribution[d] for d in diffs]
        hold_diff_counts = [hold_suite.difficulty_distribution[d] for d in diffs]

        p_opt_diff = np.array(opt_diff_counts) / len(opt_suite)
        p_hold_diff = np.array(hold_diff_counts) / len(hold_suite)

        # Max marginal difference must be small
        max_diff_delta = np.max(np.abs(p_opt_diff - p_hold_diff))
        assert max_diff_delta <= 0.08, f"Max difficulty proportion delta {max_diff_delta} exceeds 0.08"

        # Jensen-Shannon Divergence must be < 0.05
        jsd_diff = jensen_shannon_divergence(p_opt_diff, p_hold_diff)
        assert jsd_diff < 0.05, f"Difficulty JSD {jsd_diff} exceeds 0.05"

    def test_chi_square_goodness_of_fit_p_value(self, balanced_100_suite: BenchmarkSuite):
        splitter = StratifiedSplitter(holdout_ratio=0.30, random_seed=42)
        opt_suite, hold_suite = splitter.split(balanced_100_suite)

        diffs = [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD, DifficultyLevel.EXPERT]
        observed = np.array([hold_suite.difficulty_distribution[d] for d in diffs], dtype=float)
        # Target expected counts under null hypothesis
        pop_p = np.array([balanced_100_suite.difficulty_distribution[d] / len(balanced_100_suite) for d in diffs])
        expected = pop_p * len(hold_suite)

        chi2_stat = np.sum((observed - expected) ** 2 / expected)
        p_val = chi2_survival(float(chi2_stat), df=len(diffs) - 1)

        # Null hypothesis of identical distribution cannot be rejected (p > 0.05)
        assert p_val > 0.05, f"Holdout difficulty Chi-Square p-value {p_val:.4f} <= 0.05 (failed balance test)"


class TestSplitterEdgeCases:
    def test_tiny_suite_split(self, sample_verification_spec: VerificationSpec):
        tasks = [
            ATIFTask(
                task_id=f"t{i}",
                instruction=f"Task {i}",
                difficulty=DifficultyLevel.EASY,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=sample_verification_spec,
            )
            for i in range(3)
        ]
        suite = BenchmarkSuite(name="tiny", tasks=tasks)
        splitter = StratifiedSplitter(holdout_ratio=0.30)
        opt, hold = splitter.split(suite)

        assert len(opt) + len(hold) == 3
        assert len(hold) >= 1
        assert set(opt.task_ids).isdisjoint(set(hold.task_ids))

    def test_all_singletons_suite_split(self, sample_verification_spec: VerificationSpec):
        # 8 tasks, each with unique composite stratum key
        diffs = list(DifficultyLevel)
        tags = list(BehavioralTag)
        tasks = []
        for i in range(8):
            tasks.append(
                ATIFTask(
                    task_id=f"singleton-{i}",
                    instruction=f"Single task {i}",
                    difficulty=diffs[i % len(diffs)],
                    behavioral_tags=[tags[i % len(tags)]],
                    verification=sample_verification_spec,
                )
            )
        suite = BenchmarkSuite(name="all-singletons", tasks=tasks)
        splitter = StratifiedSplitter(holdout_ratio=0.30, random_seed=42)
        opt, hold = splitter.split(suite)

        assert len(opt) + len(hold) == len(suite)
        assert set(opt.task_ids).isdisjoint(set(hold.task_ids))

    def test_empty_suite_split_raises(self):
        empty_suite = BenchmarkSuite(name="empty", tasks=[])
        splitter = StratifiedSplitter()
        with pytest.raises(ValueError, match="at least 2 tasks"):
            splitter.split(empty_suite)


# =============================================================================
# Challenger Findings Regression Test Suite (Iteration 2)
# =============================================================================

class TestChallengerRegressionSuite:
    """Regression test suite validating all 5 Challenger defects identified in Iteration 1.

    Covers:
    1. Small holdout ratio (rho = 0.001, 0.01) on dense suites yields non-empty holdout (|D_hold| >= 1).
    2. High holdout ratio (rho = 0.95, 0.99) yields exact target holdout count (|D_hold| = N - 1).
    3. load_suite("") and load_suite("   ") cleanly raises SuiteLoadError without disk crawl.
    4. splitter.split([dup_t1, dup_t2]) raises ValueError on duplicate task IDs in raw sequences.
    5. compute_divergence() on empty partitions guarantees is_balanced = False.
    """

    def test_small_holdout_ratio_dense_suite_non_empty_partitions(
        self, sample_verification_spec: VerificationSpec
    ):
        """Challenger Finding 1: Ensure small holdout ratios yield non-empty holdout sets on dense suites."""
        # 20 tasks partitioned into 4 dense strata of 5 tasks each
        diffs = [DifficultyLevel.EASY, DifficultyLevel.HARD]
        tags = [BehavioralTag.TOOL_SELECTION, BehavioralTag.STATE_MUTATION]
        tasks = []
        idx = 0
        for d in diffs:
            for t in tags:
                for _ in range(5):
                    tasks.append(
                        ATIFTask(
                            task_id=f"dense-{idx:03d}",
                            instruction=f"Dense task {idx}",
                            difficulty=d,
                            behavioral_tags=[t],
                            verification=sample_verification_spec,
                        )
                    )
                    idx += 1

        suite = BenchmarkSuite(name="dense-20-suite", tasks=tasks)
        assert len(suite) == 20

        # Test both rho = 0.001 and rho = 0.01
        for small_rho in [0.001, 0.01, 0.04]:
            splitter = StratifiedSplitter(holdout_ratio=small_rho, random_seed=42)
            result = splitter.split(suite)

            # Invariant: Both partitions must be non-empty
            assert len(result.holdout_tasks) >= 1, (
                f"Holdout partition is empty for small holdout_ratio={small_rho} on dense suite!"
            )
            assert len(result.optimization_tasks) >= 1, (
                f"Optimization partition is empty for small holdout_ratio={small_rho}!"
            )

            # Invariant: Total tasks preserved
            assert len(result.optimization_tasks) + len(result.holdout_tasks) == 20
            # Invariant: Disjoint task IDs
            opt_ids = {t.task_id for t in result.optimization_tasks}
            hold_ids = {t.task_id for t in result.holdout_tasks}
            assert opt_ids.isdisjoint(hold_ids)
            assert result.divergence_report.is_leak_free is True

    def test_high_holdout_ratio_dense_suite_exact_holdout_count(
        self, sample_verification_spec: VerificationSpec
    ):
        """Challenger Finding 2: High holdout ratio yields exact target holdout count (N - 1)."""
        # Suite 1: 20 tasks, 2 dense strata of 10 tasks each
        tasks_20 = [
            ATIFTask(
                task_id=f"t20-{i:02d}",
                instruction=f"Task {i}",
                difficulty=DifficultyLevel.EASY if i < 10 else DifficultyLevel.HARD,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=sample_verification_spec,
            )
            for i in range(20)
        ]
        suite_20 = BenchmarkSuite(name="dense-20", tasks=tasks_20)

        # rho = 0.95 on N=20: round(20 * 0.95) = 19 -> target_holdout = 19 (N - 1)
        splitter_95 = StratifiedSplitter(holdout_ratio=0.95, random_seed=42)
        res_95 = splitter_95.split(suite_20)

        assert len(res_95.holdout_tasks) == 19, (
            f"Expected exactly 19 holdout tasks for rho=0.95 on N=20, got {len(res_95.holdout_tasks)}"
        )
        assert len(res_95.optimization_tasks) == 1
        assert res_95.divergence_report.is_leak_free is True

        # Suite 2: 50 tasks, 5 dense strata of 10 tasks each
        diffs = [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD, DifficultyLevel.EXPERT]
        tasks_50 = [
            ATIFTask(
                task_id=f"t50-{i:02d}",
                instruction=f"Task {i}",
                difficulty=diffs[i % len(diffs)],
                behavioral_tags=[BehavioralTag.TOOL_SELECTION if i % 2 == 0 else BehavioralTag.STATE_MUTATION],
                verification=sample_verification_spec,
            )
            for i in range(50)
        ]
        suite_50 = BenchmarkSuite(name="dense-50", tasks=tasks_50)

        # rho = 0.99 on N=50: round(50 * 0.99) = 50 -> clamped to N - 1 = 49
        splitter_99 = StratifiedSplitter(holdout_ratio=0.99, random_seed=42)
        res_99 = splitter_99.split(suite_50)

        assert len(res_99.holdout_tasks) == 49, (
            f"Expected exactly 49 holdout tasks for rho=0.99 on N=50, got {len(res_99.holdout_tasks)}"
        )
        assert len(res_99.optimization_tasks) == 1
        assert res_99.divergence_report.is_leak_free is True

    def test_load_suite_empty_and_whitespace_targets_raise_suite_load_error(self):
        """Challenger Finding 3: load_suite("") and whitespace-only targets raise SuiteLoadError without disk crawl."""
        empty_targets = ["", "   ", "\t", "  \n  \t  "]
        for target in empty_targets:
            with pytest.raises(SuiteLoadError, match="(?i)empty or whitespace only"):
                load_suite(target)

        # Verify direct loader helper functions also reject empty string
        with pytest.raises(SuiteLoadError, match="(?i)empty or whitespace only"):
            load_suite_from_directory("")

        with pytest.raises(SuiteLoadError, match="(?i)empty or whitespace only"):
            load_suite_from_file("")

    def test_split_raw_sequence_with_duplicate_task_ids_raises_value_error(
        self, sample_verification_spec: VerificationSpec
    ):
        """Challenger Finding 4: splitter.split() on raw sequence with duplicate IDs raises ValueError."""
        t1 = ATIFTask(
            task_id="dup-task-id",
            instruction="Task duplicate instance 1",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=sample_verification_spec,
        )
        t2 = ATIFTask(
            task_id="dup-task-id",
            instruction="Task duplicate instance 2",
            difficulty=DifficultyLevel.HARD,
            behavioral_tags=[BehavioralTag.STATE_MUTATION],
            verification=sample_verification_spec,
        )

        splitter = StratifiedSplitter(holdout_ratio=0.50, random_seed=42)

        # Raw sequence containing duplicates must fail fast before partitioning
        with pytest.raises(ValueError, match="(?i)duplicate task"):
            splitter.split([t1, t2])

        # Larger sequence containing one duplicate pair
        tasks = [
            ATIFTask(
                task_id=f"task-{i}",
                instruction=f"Instruction {i}",
                difficulty=DifficultyLevel.EASY,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=sample_verification_spec,
            )
            for i in range(10)
        ]
        # Introduce a duplicate ID at index 8
        tasks[8] = ATIFTask(
            task_id="task-2",  # Duplicate of tasks[2]
            instruction="Duplicate instruction",
            difficulty=DifficultyLevel.HARD,
            behavioral_tags=[BehavioralTag.STATE_MUTATION],
            verification=sample_verification_spec,
        )

        with pytest.raises(ValueError, match="(?i)duplicate task"):
            splitter.split(tasks)

    def test_empty_partition_divergence_reports_is_balanced_false(
        self, sample_verification_spec: VerificationSpec
    ):
        """Challenger Finding 5: compute_divergence with empty partition guarantees is_balanced = False."""
        t1 = ATIFTask(
            task_id="task-01",
            instruction="Instruction 1",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=sample_verification_spec,
        )
        t2 = ATIFTask(
            task_id="task-02",
            instruction="Instruction 2",
            difficulty=DifficultyLevel.HARD,
            behavioral_tags=[BehavioralTag.STATE_MUTATION],
            verification=sample_verification_spec,
        )

        splitter = StratifiedSplitter(holdout_ratio=0.50, random_seed=42)

        # Case 1: Empty holdout partition
        report_empty_hold = splitter.compute_divergence(
            all_tasks=[t1, t2],
            opt_tasks=[t1, t2],
            hold_tasks=[],
        )
        assert report_empty_hold.is_balanced is False, (
            "compute_divergence must report is_balanced=False when holdout partition is empty!"
        )

        # Case 2: Empty optimization partition
        report_empty_opt = splitter.compute_divergence(
            all_tasks=[t1, t2],
            opt_tasks=[],
            hold_tasks=[t1, t2],
        )
        assert report_empty_opt.is_balanced is False, (
            "compute_divergence must report is_balanced=False when optimization partition is empty!"
        )

