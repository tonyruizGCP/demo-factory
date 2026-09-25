"""Adversarial stress and boundary tests for Milestone 1 BenchHub.

Stress dimensions:
1. Malformed YAML/JSON (deeply nested, invalid types, empty docs, non-dict root, null bytes, unicode).
2. Duplicate task IDs under RAISE, OVERWRITE, IGNORE policies.
3. Extreme suites (N=2, N=3, N=10,000, all singletons, all identical strata).
4. Degenerate distributions (single difficulty, single tag, zero variance, all tags).
5. Memory, immutability, and partition contamination checks.
"""

from __future__ import annotations

import gc
import json
import time
from pathlib import Path
from typing import Any, Dict, List
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
    suite_to_dict,
    suite_to_json,
    suite_to_yaml,
)
from harness_optimizer.benchhub.splitter import (
    DivergenceReport,
    SplitResult,
    StratifiedSplitter,
    jensen_shannon_divergence,
    chi_square_contingency,
)


@pytest.fixture
def default_vspec() -> VerificationSpec:
    return VerificationSpec(command="echo 'grade test'")


# =============================================================================
# 1. Malformed YAML / JSON Boundary Tests
# =============================================================================

class TestMalformedAndBoundaryInputs:
    def test_empty_string_target_behavior(self):
        """Empty string input to load_suite()."""
        # Testing if load_suite("") raises or fails
        try:
            res = load_suite("")
            # If it didn't raise, check what it returned
            assert False, f"load_suite('') should not succeed, returned {res}"
        except (SuiteLoadError, ValueError) as e:
            # Expected to raise SuiteLoadError or ValueError
            pass

    def test_empty_json_file(self, tmp_path: Path):
        """0-byte empty JSON file."""
        empty_json = tmp_path / "empty.json"
        empty_json.write_text("", encoding="utf-8")
        with pytest.raises(SuiteLoadError):
            load_suite_from_file(empty_json)

    def test_empty_yaml_file(self, tmp_path: Path):
        """0-byte empty YAML file."""
        empty_yaml = tmp_path / "empty.yaml"
        empty_yaml.write_text("", encoding="utf-8")
        suite = load_suite_from_file(empty_yaml)
        assert len(suite) == 0

    def test_json_primitive_roots(self):
        for primitive in ["123", "true", "false", "null", '"just a string"']:
            with pytest.raises(SuiteLoadError, match="root must be dict or list"):
                load_suite_from_json_string(primitive)

    def test_empty_json_dict_and_list(self):
        with pytest.raises(SuiteValidationError):
            load_suite_from_json_string("{}")
        suite = load_suite_from_json_string("[]")
        assert len(suite) == 0

    def test_empty_yaml_documents(self):
        suite = load_suite_from_yaml_string("")
        assert len(suite) == 0

        yaml_empty_docs = "---\n---\n---\n"
        suite = load_suite_from_yaml_string(yaml_empty_docs)
        assert len(suite) == 0

    def test_deeply_nested_metadata(self, default_vspec: VerificationSpec):
        nested: Dict[str, Any] = {"leaf": "deep_value"}
        for i in range(100):
            nested = {"level": i, "child": nested}

        task = ATIFTask(
            task_id="deeply-nested",
            instruction="Task with 100-level nested metadata",
            difficulty=DifficultyLevel.HARD,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=default_vspec,
            metadata=nested,
        )
        suite = BenchmarkSuite(name="deep-meta", tasks=[task])
        serialized = suite_to_json(suite)
        reloaded = load_suite_from_json_string(serialized)
        assert reloaded["deeply-nested"].metadata["level"] == 99

    def test_unicode_and_special_characters(self, default_vspec: VerificationSpec):
        unicode_inst = "Instruction with 🚀 漢字 العربية \u0000 escaped \t \n special symbols: <>&\"'/\t"
        task = ATIFTask(
            task_id="unicode-task-🌟-123",
            instruction=unicode_inst,
            difficulty=DifficultyLevel.EXPERT,
            behavioral_tags=[BehavioralTag.CONSTRAINT_ADHERENCE],
            verification=default_vspec,
            metadata={"unicode_key_🔑": "unicode_val_🎯"},
        )
        suite = BenchmarkSuite(name="unicode-suite", tasks=[task])
        j_str = suite_to_json(suite)
        j_loaded = load_suite_from_json_string(j_str)
        assert j_loaded[0].task_id == "unicode-task-🌟-123"
        assert "unicode_key_🔑" in j_loaded[0].metadata

        y_str = suite_to_yaml(suite)
        y_loaded = load_suite_from_yaml_string(y_str)
        assert y_loaded[0].task_id == "unicode-task-🌟-123"
        assert "unicode_key_🔑" in y_loaded[0].metadata

    def test_yaml_anchor_and_alias(self):
        yaml_content = """
base_verification: &base_v
  command: pytest -v

tasks:
  - task_id: task-anchor-1
    instruction: Test anchor 1
    difficulty: EASY
    behavioral_tags: [tool_selection]
    verification: *base_v
  - task_id: task-anchor-2
    instruction: Test anchor 2
    difficulty: MEDIUM
    behavioral_tags: [state_mutation]
    verification: *base_v
"""
        suite = load_suite_from_yaml_string(yaml_content)
        assert len(suite) == 2
        assert suite["task-anchor-1"].verification.command == "pytest -v"
        assert suite["task-anchor-2"].verification.command == "pytest -v"


# =============================================================================
# 2. Duplicate Task IDs Under Policies
# =============================================================================

class TestDuplicatePolicyStress:
    def test_duplicate_policies_in_json_list(self):
        tasks_json = json.dumps([
            {
                "task_id": "dup-id",
                "instruction": "First occurrence",
                "difficulty": "EASY",
                "behavioral_tags": ["tool_selection"],
                "verification": {"command": "echo 1"},
            },
            {
                "task_id": "dup-id",
                "instruction": "Second occurrence",
                "difficulty": "HARD",
                "behavioral_tags": ["state_mutation"],
                "verification": {"command": "echo 2"},
            },
        ])

        # RAISE
        with pytest.raises(DuplicateTaskError) as exc_info:
            load_suite_from_json_string(tasks_json, on_duplicate=DuplicatePolicy.RAISE)
        assert exc_info.value.task_id == "dup-id"

        # OVERWRITE
        suite_over = load_suite_from_json_string(tasks_json, on_duplicate=DuplicatePolicy.OVERWRITE)
        assert len(suite_over) == 1
        assert suite_over["dup-id"].instruction == "Second occurrence"
        assert suite_over["dup-id"].difficulty == DifficultyLevel.HARD

        # IGNORE
        suite_ign = load_suite_from_json_string(tasks_json, on_duplicate=DuplicatePolicy.IGNORE)
        assert len(suite_ign) == 1
        assert suite_ign["dup-id"].instruction == "First occurrence"
        assert suite_ign["dup-id"].difficulty == DifficultyLevel.EASY

    def test_duplicate_policies_across_multi_document_yaml(self):
        yaml_content = """
task_id: yaml-dup
instruction: First yaml doc
difficulty: EASY
behavioral_tags: [tool_selection]
verification: {command: "test"}
---
task_id: yaml-dup
instruction: Second yaml doc
difficulty: EXPERT
behavioral_tags: [multi_step_retrieval]
verification: {command: "test"}
"""
        with pytest.raises(DuplicateTaskError):
            load_suite_from_yaml_string(yaml_content, on_duplicate="raise")

        suite_over = load_suite_from_yaml_string(yaml_content, on_duplicate="overwrite")
        assert suite_over["yaml-dup"].difficulty == DifficultyLevel.EXPERT

        suite_ign = load_suite_from_yaml_string(yaml_content, on_duplicate="ignore")
        assert suite_ign["yaml-dup"].difficulty == DifficultyLevel.EASY

    def test_invalid_duplicate_policy_string_raises(self):
        with pytest.raises(ValueError):
            load_suite_from_json_string("[]", on_duplicate="invalid_mode")


# =============================================================================
# 3. Extreme Suite Sizes & Zero Variance Distributions
# =============================================================================

class TestExtremeSuitesAndDegenerateDistributions:
    def test_size_2_suite_split(self, default_vspec: VerificationSpec):
        t1 = ATIFTask(
            task_id="t1",
            instruction="Task 1",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=default_vspec,
        )
        t2 = ATIFTask(
            task_id="t2",
            instruction="Task 2",
            difficulty=DifficultyLevel.HARD,
            behavioral_tags=[BehavioralTag.STATE_MUTATION],
            verification=default_vspec,
        )
        suite = BenchmarkSuite(name="size-2", tasks=[t1, t2])
        splitter = StratifiedSplitter(holdout_ratio=0.5, random_seed=42)
        opt, hold = splitter.split(suite)

        assert len(opt) == 1
        assert len(hold) == 1
        assert opt.task_ids[0] != hold.task_ids[0]
        assert splitter.verify_non_leakage(opt.tasks, hold.tasks)

    def test_size_3_suite_split(self, default_vspec: VerificationSpec):
        tasks = [
            ATIFTask(
                task_id=f"t{i}",
                instruction=f"Task {i}",
                difficulty=DifficultyLevel.MEDIUM,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=default_vspec,
            )
            for i in range(3)
        ]
        suite = BenchmarkSuite(name="size-3", tasks=tasks)
        splitter = StratifiedSplitter(holdout_ratio=0.33, random_seed=42)
        opt, hold = splitter.split(suite)

        assert len(opt) + len(hold) == 3
        assert len(hold) == 1
        assert len(opt) == 2
        assert set(opt.task_ids).isdisjoint(set(hold.task_ids))

    def test_zero_variance_single_difficulty_and_single_tag(self, default_vspec: VerificationSpec):
        N = 200
        tasks = [
            ATIFTask(
                task_id=f"monolithic-{i:03d}",
                instruction="Identical distribution task",
                difficulty=DifficultyLevel.MEDIUM,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=default_vspec,
            )
            for i in range(N)
        ]
        suite = BenchmarkSuite(name="zero-variance-suite", tasks=tasks)
        splitter = StratifiedSplitter(holdout_ratio=0.30, random_seed=42)
        result = splitter.split(suite)

        assert len(result.optimization_tasks) == 140
        assert len(result.holdout_tasks) == 60
        assert result.divergence_report.is_leak_free
        assert result.divergence_report.difficulty_jsd == 0.0
        assert result.divergence_report.max_jsd == 0.0

    def test_all_tags_per_task(self, default_vspec: VerificationSpec):
        N = 100
        all_tags = [
            BehavioralTag.TOOL_SELECTION,
            BehavioralTag.MULTI_STEP_RETRIEVAL,
            BehavioralTag.STATE_MUTATION,
            BehavioralTag.CONSTRAINT_ADHERENCE,
        ]
        tasks = [
            ATIFTask(
                task_id=f"all-tags-{i:03d}",
                instruction="Task exercising every capability",
                difficulty=DifficultyLevel.EASY if i % 2 == 0 else DifficultyLevel.HARD,
                behavioral_tags=all_tags,
                verification=default_vspec,
            )
            for i in range(N)
        ]
        suite = BenchmarkSuite(name="all-tags-suite", tasks=tasks)
        splitter = StratifiedSplitter(holdout_ratio=0.30, random_seed=42)
        result = splitter.split(suite)

        assert result.divergence_report.is_leak_free
        assert len(result.optimization_tasks) == 70
        assert len(result.holdout_tasks) == 30
        for tag_name, jsd in result.divergence_report.tag_jsds.items():
            assert jsd == 0.0, f"Tag {tag_name} JSD expected 0.0, got {jsd}"

    def test_all_singletons_large(self, default_vspec: VerificationSpec):
        diffs = list(DifficultyLevel)
        all_tags = list(BehavioralTag)

        tasks = []
        task_idx = 0
        for d in diffs:
            for t1 in all_tags:
                tasks.append(
                    ATIFTask(
                        task_id=f"single-{task_idx}",
                        instruction=f"Single task {task_idx}",
                        difficulty=d,
                        behavioral_tags=[t1],
                        verification=default_vspec,
                    )
                )
                task_idx += 1
            for i, t1 in enumerate(all_tags):
                for t2 in all_tags[i + 1:]:
                    tasks.append(
                        ATIFTask(
                            task_id=f"single-{task_idx}",
                            instruction=f"Single combo {task_idx}",
                            difficulty=d,
                            behavioral_tags=[t1, t2],
                            verification=default_vspec,
                        )
                    )
                    task_idx += 1

        suite = BenchmarkSuite(name="all-singletons-expanded", tasks=tasks)
        strata = suite.get_strata()
        for k, v in strata.items():
            assert len(v) == 1, f"Stratum {k} is not a singleton: len={len(v)}"

        splitter = StratifiedSplitter(holdout_ratio=0.30, random_seed=42)
        opt, hold = splitter.split(suite)

        assert len(opt) + len(hold) == len(tasks)
        assert splitter.verify_non_leakage(opt.tasks, hold.tasks)
        expected_hold = round(len(tasks) * 0.30)
        assert len(hold) == expected_hold

    def test_scale_10000_tasks_stress_and_performance(self, default_vspec: VerificationSpec):
        N = 10_000
        diffs = list(DifficultyLevel)
        tags = list(BehavioralTag)

        start_gen = time.perf_counter()
        tasks = [
            ATIFTask(
                task_id=f"scale-task-{i:05d}",
                instruction=f"Synthetic instruction for task {i}",
                difficulty=diffs[i % len(diffs)],
                behavioral_tags=[tags[i % len(tags)], tags[(i + 1) % len(tags)]],
                verification=default_vspec,
            )
            for i in range(N)
        ]
        suite = BenchmarkSuite(name="scale-10k", tasks=tasks)
        gen_time = time.perf_counter() - start_gen

        start_split = time.perf_counter()
        splitter = StratifiedSplitter(holdout_ratio=0.30, random_seed=42)
        result = splitter.split(suite)
        split_time = time.perf_counter() - start_split

        assert split_time < 2.0, f"Stratified split on 10,000 tasks took {split_time:.2f}s (exceeds 2.0s threshold)"
        assert len(result.optimization_tasks) == 7000
        assert len(result.holdout_tasks) == 3000
        assert result.divergence_report.is_leak_free
        assert result.divergence_report.max_jsd < 0.01

    def test_skewed_ratios_small_dense_strata(self, default_vspec: VerificationSpec):
        """Test high holdout ratio (0.80) with small dense strata of size 2."""
        tasks = [
            ATIFTask(
                task_id=f"task-dense1-{i}",
                instruction="Pair 1",
                difficulty=DifficultyLevel.EASY,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=default_vspec,
            )
            for i in range(2)
        ] + [
            ATIFTask(
                task_id=f"task-dense2-{i}",
                instruction="Pair 2",
                difficulty=DifficultyLevel.HARD,
                behavioral_tags=[BehavioralTag.STATE_MUTATION],
                verification=default_vspec,
            )
            for i in range(2)
        ]
        suite = BenchmarkSuite(name="skewed-pairs", tasks=tasks)
        splitter = StratifiedSplitter(holdout_ratio=0.75, random_seed=42)
        opt, hold = splitter.split(suite)

        assert len(opt) + len(hold) == 4
        assert splitter.verify_non_leakage(opt.tasks, hold.tasks)


# =============================================================================
# 4. Immutability & Partition Contamination Checks
# =============================================================================

class TestPartitionContaminationAndImmutability:
    def test_partition_contamination_after_split(self, default_vspec: VerificationSpec):
        tasks = [
            ATIFTask(
                task_id="task-opt-candidate",
                instruction="Original instruction",
                difficulty=DifficultyLevel.EASY,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=default_vspec,
                metadata={"status": "initial"},
            ),
            ATIFTask(
                task_id="task-hold-candidate",
                instruction="Original instruction",
                difficulty=DifficultyLevel.HARD,
                behavioral_tags=[BehavioralTag.STATE_MUTATION],
                verification=default_vspec,
                metadata={"status": "initial"},
            ),
        ]
        suite = BenchmarkSuite(name="isolation-test", tasks=tasks)
        splitter = StratifiedSplitter(holdout_ratio=0.5, random_seed=42)
        opt_suite, hold_suite = splitter.split(suite)

        assert len(opt_suite) == 1
        assert len(hold_suite) == 1
        assert opt_suite[0].task_id != hold_suite[0].task_id

        opt_task = opt_suite[0]
        opt_task.metadata["status"] = "mutated_in_optimization"

        hold_task = hold_suite[0]
        assert hold_task.metadata.get("status") == "initial"

    def test_split_with_direct_sequence_of_tasks(self, default_vspec: VerificationSpec):
        tasks = [
            ATIFTask(
                task_id=f"seq-task-{i}",
                instruction=f"Instruction {i}",
                difficulty=DifficultyLevel.EASY,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=default_vspec,
            )
            for i in range(10)
        ]
        splitter = StratifiedSplitter(holdout_ratio=0.30, random_seed=42)
        res = splitter.split(tasks)

        assert len(res.optimization_tasks) == 7
        assert len(res.holdout_tasks) == 3
        assert res.divergence_report.is_leak_free
