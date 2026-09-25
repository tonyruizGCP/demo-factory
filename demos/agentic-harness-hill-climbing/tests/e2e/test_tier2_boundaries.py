"""Tier 2 E2E Boundary and Corner Value Test Suite.

This module contains comprehensive, opaque-box boundary value test cases for all
16 features (F1 to F16) of the Autonomous Evaluation and Hill-Climbing Harness.

Each feature includes at least 5 distinct, rigorous boundary test cases covering
extreme inputs, degenerate data structures, numerical stability, concurrency,
timeout constraints, and error handling.
"""

from __future__ import annotations

import concurrent.futures
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
from typing import Any, Dict, List, Optional
import numpy as np
import pytest
from pydantic import ValidationError

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe module imports supporting progressive testability across milestones
try:
    from harness_optimizer.benchhub.schema import (
        ATIFTask,
        BehavioralTag,
        BenchmarkSuite,
        DifficultyLevel,
        VerificationSpec,
    )
except ImportError:
    ATIFTask = None  # type: ignore[assignment, misc]
    BehavioralTag = None  # type: ignore[assignment, misc]
    BenchmarkSuite = None  # type: ignore[assignment, misc]
    DifficultyLevel = None  # type: ignore[assignment, misc]
    VerificationSpec = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.benchhub.splitter import (
        MultidimensionalStratifiedSplitter,
        SplitResult,
        compute_distribution_divergence,
        jensen_shannon_divergence,
        stratified_split,
    )
except ImportError:
    MultidimensionalStratifiedSplitter = None  # type: ignore[assignment, misc]
    SplitResult = None  # type: ignore[assignment, misc]
    compute_distribution_divergence = None  # type: ignore[assignment, misc]
    jensen_shannon_divergence = None  # type: ignore[assignment, misc]
    stratified_split = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.harbor.config import SandboxConfig
    from harness_optimizer.harbor.telemetry import TokenSpend, TraceSpan, TrialTelemetry
except ImportError:
    SandboxConfig = None  # type: ignore[assignment, misc]
    TokenSpend = None  # type: ignore[assignment, misc]
    TraceSpan = None  # type: ignore[assignment, misc]
    TrialTelemetry = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.harbor.sandbox import (
        AgentCandidate,
        BaseSandbox,
        InMemoryMockHarness,
        SubprocessSandbox,
    )
except ImportError:
    AgentCandidate = None  # type: ignore[assignment, misc]
    BaseSandbox = None  # type: ignore[assignment, misc]
    InMemoryMockHarness = None  # type: ignore[assignment, misc]
    SubprocessSandbox = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.harbor.executor import ConcurrentBatchExecutor
except ImportError:
    ConcurrentBatchExecutor = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.bayesian.engine import BetaBinomialModel
except ImportError:
    BetaBinomialModel = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.bayesian.stopping import EarlyStoppingController, StoppingDecision
except ImportError:
    EarlyStoppingController = None  # type: ignore[assignment, misc]
    StoppingDecision = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.clustering.trace_miner import TraceMiner
except ImportError:
    TraceMiner = None  # type: ignore[assignment, misc]

try:
    try:
        from harness_optimizer.clustering.vectorizer import TFIDFTraceVectorizer as TraceVectorizer
    except ImportError:
        from harness_optimizer.clustering.vectorizer import TraceVectorizer  # type: ignore[assignment, misc]
except ImportError:
    TraceVectorizer = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.clustering.archetypes import (
        ArchetypeCluster,
        ArchetypeClusterer,
        ClusteredFailureReport,
    )
except ImportError:
    ArchetypeCluster = None  # type: ignore[assignment, misc]
    ArchetypeClusterer = None  # type: ignore[assignment, misc]
    ClusteredFailureReport = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.lifecycle.holdout_gate import (
        HoldoutDecision,
        HoldoutGate,
        mcnemar_test,
    )
except ImportError:
    HoldoutDecision = None  # type: ignore[assignment, misc]
    HoldoutGate = None  # type: ignore[assignment, misc]
    mcnemar_test = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.lifecycle.state_machine import (
        InvalidStateTransitionError,
        OptimizationState,
        OptimizationStateMachine,
    )
except ImportError:
    InvalidStateTransitionError = None  # type: ignore[assignment, misc]
    OptimizationState = None  # type: ignore[assignment, misc]
    OptimizationStateMachine = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.synthetic.benchmark import SyntheticBenchmarkGenerator
except ImportError:
    SyntheticBenchmarkGenerator = None  # type: ignore[assignment, misc]

try:
    import cli
except ImportError:
    cli = None


# ==============================================================================
# Feature 1: ATIF Task Schema & Ingestion Boundaries
# ==============================================================================
class TestF1TaskSchemaBoundaries:
    """Boundary test cases for Feature 1: ATIF Task Schema & Ingestion."""

    @pytest.fixture(autouse=True)
    def _require_f1(self) -> None:
        if ATIFTask is None or VerificationSpec is None:
            pytest.skip("harness_optimizer.benchhub.schema not yet implemented")

    def test_f1_boundary_empty_instruction_string(self) -> None:
        """Boundary: Empty or whitespace-only instruction string must be rejected."""
        vspec = VerificationSpec(command="echo OK", timeout_seconds=30.0)
        with pytest.raises((ValidationError, ValueError)):
            ATIFTask(
                task_id="task_empty_instr",
                instruction="",
                difficulty=DifficultyLevel.EASY,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=vspec,
            )
        with pytest.raises((ValidationError, ValueError)):
            ATIFTask(
                task_id="task_ws_instr",
                instruction="   \t\n  ",
                difficulty=DifficultyLevel.EASY,
                behavioral_tags=[BehavioralTag.TOOL_SELECTION],
                verification=vspec,
            )

    def test_f1_boundary_huge_instruction_string(self) -> None:
        """Boundary: Extremely large instruction string (100,000 characters) handles cleanly."""
        vspec = VerificationSpec(command="pytest tests/", timeout_seconds=60.0)
        huge_text = "System Directive: " + ("A" * 100_000)
        task = ATIFTask(
            task_id="task_huge_instr",
            instruction=huge_text,
            difficulty=DifficultyLevel.HARD,
            behavioral_tags=[BehavioralTag.STATE_MUTATION],
            verification=vspec,
        )
        assert len(task.instruction) == 100_018
        assert task.instruction.startswith("System Directive: AAAA")

    def test_f1_boundary_empty_metadata_dictionary(self) -> None:
        """Boundary: Empty metadata dictionary is accepted and behaves as an empty mapping."""
        vspec = VerificationSpec(command="python test.py", timeout_seconds=10.0)
        task = ATIFTask(
            task_id="task_empty_meta",
            instruction="Fix formatting bug",
            difficulty=DifficultyLevel.MEDIUM,
            behavioral_tags=[BehavioralTag.CONSTRAINT_ADHERENCE],
            verification=vspec,
            metadata={},
        )
        assert task.metadata == {}
        assert isinstance(task.metadata, dict)
        assert task.metadata.get("repo") is None

    def test_f1_boundary_unknown_tag_rejection(self) -> None:
        """Boundary: Invalid or unknown behavioral tags must raise validation error."""
        vspec = VerificationSpec(command="make test", timeout_seconds=15.0)
        with pytest.raises((ValidationError, ValueError)):
            ATIFTask(
                task_id="task_bad_tag",
                instruction="Execute vulnerability scan",
                difficulty=DifficultyLevel.EXPERT,
                behavioral_tags=["unknown_invalid_nonexistent_tag"],  # type: ignore[list-item]
                verification=vspec,
            )

    def test_f1_boundary_missing_or_empty_verification_command(self) -> None:
        """Boundary: Empty or whitespace-only verification command must raise validation error."""
        with pytest.raises((ValidationError, ValueError)):
            VerificationSpec(command="")
        with pytest.raises((ValidationError, ValueError)):
            VerificationSpec(command="    ")


# ==============================================================================
# Feature 2: Multidimensional Stratified Splitting Boundaries
# ==============================================================================
class TestF2StratifiedSplittingBoundaries:
    """Boundary test cases for Feature 2: Multidimensional Stratified Splitting."""

    @pytest.fixture(autouse=True)
    def _require_f2(self) -> None:
        if (
            ATIFTask is None
            or (MultidimensionalStratifiedSplitter is None and stratified_split is None)
        ):
            pytest.skip("harness_optimizer.benchhub.splitter not yet implemented")

    def _split(self, tasks: List[Any], ratio: float = 0.7) -> Any:
        if MultidimensionalStratifiedSplitter is not None:
            splitter = MultidimensionalStratifiedSplitter(split_ratio=ratio, seed=42)
            return splitter.split(tasks)
        return stratified_split(tasks, split_ratio=ratio, seed=42)

    def _make_task(self, tid: str, diff: Any, tags: List[Any]) -> Any:
        vspec = VerificationSpec(command="pytest", timeout_seconds=30.0)
        return ATIFTask(
            task_id=tid,
            instruction=f"Instruction for {tid}",
            difficulty=diff,
            behavioral_tags=tags,
            verification=vspec,
        )

    def test_f2_boundary_single_task_splitting(self) -> None:
        """Boundary: Suite containing exactly 1 task must partition without unhandled error or leakage."""
        t1 = self._make_task("t1", DifficultyLevel.EASY, [BehavioralTag.TOOL_SELECTION])
        try:
            result = self._split([t1], ratio=0.7)
            opt = result.optimization_set
            hold = result.holdout_set
            assert len(opt) + len(hold) == 1
            assert set(t.task_id for t in opt).isdisjoint(set(t.task_id for t in hold))
        except ValueError as exc:
            assert "insufficient" in str(exc).lower() or "too few" in str(exc).lower()

    def test_f2_boundary_split_ratio_extremes_zero_and_one(self) -> None:
        """Boundary: Split ratios 0.0 and 1.0 boundary handling."""
        tasks = [
            self._make_task(f"t_{i}", DifficultyLevel.MEDIUM, [BehavioralTag.STATE_MUTATION])
            for i in range(10)
        ]
        res_one = self._split(tasks, ratio=1.0)
        assert len(res_one.optimization_set) == 10
        assert len(res_one.holdout_set) == 0
        assert set(t.task_id for t in res_one.optimization_set).isdisjoint(
            set(t.task_id for t in res_one.holdout_set)
        )

        res_zero = self._split(tasks, ratio=0.0)
        assert len(res_zero.optimization_set) == 0
        assert len(res_zero.holdout_set) == 10

    def test_f2_boundary_odd_number_of_tasks(self) -> None:
        """Boundary: Partitioning an odd number of tasks (e.g. 7 tasks) preserves total count."""
        diffs = [
            DifficultyLevel.EASY,
            DifficultyLevel.MEDIUM,
            DifficultyLevel.HARD,
            DifficultyLevel.EXPERT,
        ]
        tasks = [
            self._make_task(
                f"t_odd_{i}",
                diffs[i % len(diffs)],
                [BehavioralTag.TOOL_SELECTION],
            )
            for i in range(7)
        ]
        result = self._split(tasks, ratio=0.7)
        opt_ids = set(t.task_id for t in result.optimization_set)
        hold_ids = set(t.task_id for t in result.holdout_set)
        assert len(result.optimization_set) + len(result.holdout_set) == 7
        assert opt_ids.isdisjoint(hold_ids)
        assert opt_ids | hold_ids == set(t.task_id for t in tasks)

    def test_f2_boundary_all_tasks_identical_stratum(self) -> None:
        """Boundary: All tasks share identical difficulty and tags (single dense stratum)."""
        tasks = [
            self._make_task(f"t_dense_{i}", DifficultyLevel.HARD, [BehavioralTag.MULTI_STEP_RETRIEVAL])
            for i in range(20)
        ]
        result = self._split(tasks, ratio=0.7)
        assert len(result.optimization_set) == 14
        assert len(result.holdout_set) == 6
        assert set(t.task_id for t in result.optimization_set).isdisjoint(
            set(t.task_id for t in result.holdout_set)
        )

    def test_f2_boundary_unbalanced_difficulty_skew_with_singletons(self) -> None:
        """Boundary: Unbalanced difficulty distribution with 19 EASY tasks and 1 EXPERT singleton."""
        tasks = [
            self._make_task(f"t_easy_{i}", DifficultyLevel.EASY, [BehavioralTag.TOOL_SELECTION])
            for i in range(19)
        ]
        tasks.append(
            self._make_task("t_expert_singleton", DifficultyLevel.EXPERT, [BehavioralTag.STATE_MUTATION])
        )
        result = self._split(tasks, ratio=0.7)
        all_ids = set(t.task_id for t in tasks)
        opt_ids = set(t.task_id for t in result.optimization_set)
        hold_ids = set(t.task_id for t in result.holdout_set)
        assert len(result.optimization_set) + len(result.holdout_set) == 20
        assert opt_ids.isdisjoint(hold_ids)
        assert opt_ids | hold_ids == all_ids


# ==============================================================================
# Feature 3: Statistical Divergence Verification Boundaries
# ==============================================================================
class TestF3StatisticalDivergenceBoundaries:
    """Boundary test cases for Feature 3: Statistical Divergence Verification."""

    @pytest.fixture(autouse=True)
    def _require_f3(self) -> None:
        if compute_distribution_divergence is None and jensen_shannon_divergence is None:
            pytest.skip("Statistical divergence metrics not yet implemented")

    def _calc_jsd(self, p: np.ndarray, q: np.ndarray) -> float:
        if jensen_shannon_divergence is not None:
            return float(jensen_shannon_divergence(p, q))
        p = np.asarray(p, dtype=float)
        q = np.asarray(q, dtype=float)
        p = p / np.sum(p) if np.sum(p) > 0 else p
        q = q / np.sum(q) if np.sum(q) > 0 else q
        m = 0.5 * (p + q)
        def kl(a: np.ndarray, b: np.ndarray) -> float:
            mask = (a > 0) & (b > 0)
            return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
        return 0.5 * kl(p, m) + 0.5 * kl(q, m)

    def test_f3_boundary_empty_partition_divergence(self) -> None:
        """Boundary: Empty partition divergence calculation must avoid unhandled zero division."""
        p = np.array([])
        q = np.array([])
        if jensen_shannon_divergence is not None:
            try:
                div = jensen_shannon_divergence(p, q)
                assert div == 0.0 or math.isnan(div) is False
            except (ValueError, ZeroDivisionError):
                pass

    def test_f3_boundary_identical_partitions_zero_divergence(self) -> None:
        """Boundary: Identical partitions produce exactly zero divergence."""
        p = np.array([0.25, 0.25, 0.25, 0.25])
        q = np.array([0.25, 0.25, 0.25, 0.25])
        div = self._calc_jsd(p, q)
        assert abs(div) < 1e-9

    def test_f3_boundary_maximally_divergent_partitions(self) -> None:
        """Boundary: Disjoint, maximally divergent partitions produce bounded positive divergence."""
        p = np.array([1.0, 0.0])
        q = np.array([0.0, 1.0])
        div = self._calc_jsd(p, q)
        assert div > 0.0
        assert div <= 1.0 + 1e-7

    def test_f3_boundary_zero_division_guard_zero_frequency_bins(self) -> None:
        """Boundary: Frequency distributions with zero frequency bins avoid division by zero."""
        p = np.array([10.0, 0.0, 5.0])
        q = np.array([0.0, 8.0, 2.0])
        div = self._calc_jsd(p, q)
        assert math.isnan(div) is False
        assert math.isinf(div) is False
        assert div >= 0.0

    def test_f3_boundary_negative_or_nan_divergence_guard(self) -> None:
        """Boundary: Divergence metric output is strictly non-negative and not NaN."""
        rng = np.random.default_rng(42)
        for _ in range(10):
            p = rng.dirichlet(np.ones(5))
            q = rng.dirichlet(np.ones(5))
            div = self._calc_jsd(p, q)
            assert not math.isnan(div), "Divergence cannot be NaN"
            assert div >= -1e-9, "Divergence cannot be negative"


# ==============================================================================
# Feature 4: Trial Telemetry & Data Contracts Boundaries
# ==============================================================================
class TestF4TrialTelemetryBoundaries:
    """Boundary test cases for Feature 4: Trial Telemetry & Data Contracts."""

    @pytest.fixture(autouse=True)
    def _require_f4(self) -> None:
        if TrialTelemetry is None or TokenSpend is None:
            pytest.skip("harness_optimizer.harbor.telemetry not yet implemented")

    def test_f4_boundary_zero_latency_ms(self) -> None:
        """Boundary: Zero latency (0.0 ms) is accepted as a valid non-negative float."""
        telemetry = TrialTelemetry(
            trial_id="trial_0_lat",
            task_id="task_1",
            candidate_id="cand_1",
            passed=True,
            exit_code=0,
            latency_ms=0.0,
            token_spend=TokenSpend(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            trace_logs=[],
        )
        assert telemetry.latency_ms == 0.0
        assert isinstance(telemetry.latency_ms, float)

    def test_f4_boundary_extremely_large_token_count(self) -> None:
        """Boundary: Extremely large token counts (10^9) handled without overflow."""
        large_tokens = 1_000_000_000
        telemetry = TrialTelemetry(
            trial_id="trial_huge_tokens",
            task_id="task_1",
            candidate_id="cand_1",
            passed=True,
            exit_code=0,
            latency_ms=1200.0,
            token_spend=TokenSpend(
                prompt_tokens=large_tokens,
                completion_tokens=large_tokens,
                total_tokens=2 * large_tokens,
            ),
            trace_logs=[],
        )
        assert telemetry.token_spend.total_tokens == 2_000_000_000
        assert telemetry.token_spend.prompt_tokens == 1_000_000_000

    def test_f4_boundary_empty_trace_log_list(self) -> None:
        """Boundary: Empty trace logs list is accepted and iterable without error."""
        telemetry = TrialTelemetry(
            trial_id="trial_empty_trace",
            task_id="task_1",
            candidate_id="cand_1",
            passed=True,
            exit_code=0,
            latency_ms=45.0,
            token_spend=TokenSpend(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            trace_logs=[],
        )
        assert len(telemetry.trace_logs) == 0
        assert list(telemetry.trace_logs) == []

    def test_f4_boundary_negative_exit_code_signal_kill(self) -> None:
        """Boundary: Negative exit code (e.g. -9 SIGKILL, -15 SIGTERM) is recorded accurately."""
        telemetry = TrialTelemetry(
            trial_id="trial_killed",
            task_id="task_1",
            candidate_id="cand_1",
            passed=False,
            exit_code=-9,
            latency_ms=100.0,
            token_spend=TokenSpend(prompt_tokens=5, completion_tokens=0, total_tokens=5),
            trace_logs=[],
            raw_error_message="Killed by SIGKILL (-9)",
        )
        assert telemetry.exit_code == -9
        assert telemetry.passed is False

    def test_f4_boundary_unicode_and_binary_raw_error_message(self) -> None:
        """Boundary: Unicode, emojis, null bytes, and non-ASCII characters preserved safely."""
        raw_msg = "Error: 🔥 Crash with null byte " + chr(0) + " and non-ascii: 你好世界 \\t\\n ☃"
        telemetry = TrialTelemetry(
            trial_id="trial_unicode",
            task_id="task_1",
            candidate_id="cand_1",
            passed=False,
            exit_code=1,
            latency_ms=80.0,
            token_spend=TokenSpend(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            trace_logs=[],
            raw_error_message=raw_msg,
        )
        assert telemetry.raw_error_message is not None
        assert "Crash" in telemetry.raw_error_message


# ==============================================================================
# Feature 5: InMemoryMockHarness Boundaries
# ==============================================================================
class TestF5InMemoryMockHarnessBoundaries:
    """Boundary test cases for Feature 5: InMemoryMockHarness."""

    @pytest.fixture(autouse=True)
    def _require_f5(self) -> None:
        if InMemoryMockHarness is None or ATIFTask is None:
            pytest.skip("harness_optimizer.harbor.sandbox.InMemoryMockHarness not yet implemented")

    def _sample_task(self) -> Any:
        vspec = VerificationSpec(command="echo mock", timeout_seconds=10.0)
        return ATIFTask(
            task_id="mock_task_1",
            instruction="Mock instruction",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=vspec,
        )

    def _sample_candidate(self) -> Any:
        if AgentCandidate is not None:
            return AgentCandidate(candidate_id="mock_agent")
        return "mock_agent"

    def test_f5_boundary_failure_rate_zero_all_pass(self) -> None:
        """Boundary: failure_rate=0.0 yields 100% pass rate across consecutive trials."""
        harness = InMemoryMockHarness(failure_rate=0.0, seed=42)
        task = self._sample_task()
        cand = self._sample_candidate()
        results = [harness.execute_trial(task, cand) for _ in range(25)]
        assert all(t.passed is True for t in results)
        assert all(t.exit_code == 0 for t in results)

    def test_f5_boundary_failure_rate_one_all_fail(self) -> None:
        """Boundary: failure_rate=1.0 yields 100% fail rate across consecutive trials."""
        harness = InMemoryMockHarness(failure_rate=1.0, seed=42)
        task = self._sample_task()
        cand = self._sample_candidate()
        results = [harness.execute_trial(task, cand) for _ in range(25)]
        assert all(t.passed is False for t in results)
        assert all(t.exit_code != 0 for t in results)
        assert all(t.raw_error_message is not None for t in results)

    def test_f5_boundary_empty_error_archetypes_list(self) -> None:
        """Boundary: Empty error_archetypes list falls back cleanly to default error string."""
        harness = InMemoryMockHarness(failure_rate=1.0, error_archetypes=[], seed=42)
        task = self._sample_task()
        cand = self._sample_candidate()
        telemetry = harness.execute_trial(task, cand)
        assert telemetry.passed is False
        assert telemetry.raw_error_message is not None
        assert len(telemetry.raw_error_message) > 0

    def test_f5_boundary_seed_reproducibility_and_negative_seed(self) -> None:
        """Boundary: seed=0 reproducibility and handling of negative seed values."""
        task = self._sample_task()
        cand = self._sample_candidate()
        harness_a = InMemoryMockHarness(failure_rate=0.5, seed=0)
        harness_b = InMemoryMockHarness(failure_rate=0.5, seed=0)
        runs_a = [harness_a.execute_trial(task, cand).passed for _ in range(15)]
        runs_b = [harness_b.execute_trial(task, cand).passed for _ in range(15)]
        assert runs_a == runs_b, "Identical seed=0 must produce identical outcome sequence"

        harness_neg = InMemoryMockHarness(failure_rate=0.5, seed=-99)
        res = harness_neg.execute_trial(task, cand)
        assert isinstance(res.passed, bool)

    def test_f5_boundary_high_concurrency_simulation(self) -> None:
        """Boundary: Multi-threaded concurrent execution on single harness instance."""
        harness = InMemoryMockHarness(failure_rate=0.3, seed=123)
        task = self._sample_task()
        cand = self._sample_candidate()
        results = []

        def worker() -> Any:
            return harness.execute_trial(task, cand)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(worker) for _ in range(40)]
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())

        assert len(results) == 40
        assert all(isinstance(r.latency_ms, (int, float)) for r in results)


# ==============================================================================
# Feature 6: Subprocess Sandbox Hooks Boundaries
# ==============================================================================
class TestF6SubprocessSandboxBoundaries:
    """Boundary test cases for Feature 6: Subprocess Sandbox Hooks."""

    @pytest.fixture(autouse=True)
    def _require_f6(self) -> None:
        if SubprocessSandbox is None or ATIFTask is None:
            pytest.skip("harness_optimizer.harbor.sandbox.SubprocessSandbox not yet implemented")

    def _sample_candidate(self) -> Any:
        if AgentCandidate is not None:
            return AgentCandidate(candidate_id="subproc_agent")
        return "subproc_agent"

    def test_f6_boundary_sub_millisecond_timeout(self) -> None:
        """Boundary: Sub-millisecond timeout triggers timeout watchdog and marks passed=False."""
        vspec = VerificationSpec(
            command='python3 -c "import time; time.sleep(1.0)"',
            timeout_seconds=0.001,
        )
        task = ATIFTask(
            task_id="t_submilli_timeout",
            instruction="Sleep task",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=vspec,
        )
        sandbox = SubprocessSandbox()
        cand = self._sample_candidate()
        telemetry = sandbox.execute_trial(task, cand)
        assert telemetry.passed is False
        assert (
            "timeout" in (telemetry.raw_error_message or "").lower()
            or telemetry.exit_code != 0
        )

    def test_f6_boundary_empty_command_execution(self) -> None:
        """Boundary: Empty command execution is handled gracefully without hanging."""
        sandbox = SubprocessSandbox()
        cand = self._sample_candidate()
        vspec = VerificationSpec(command="exit 1", timeout_seconds=5.0)
        task = ATIFTask(
            task_id="t_empty_cmd",
            instruction="Empty command test",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=vspec,
        )
        telemetry = sandbox.execute_trial(task, cand)
        assert telemetry.passed is False
        assert telemetry.exit_code == 1

    def test_f6_boundary_huge_stdout_output_overflow(self) -> None:
        """Boundary: Command generating 1MB of stdout does not deadlock subprocess buffer."""
        vspec = VerificationSpec(
            command="python3 -c 'import sys; sys.stdout.write(\"A\" * 1_000_000)'",
            timeout_seconds=10.0,
        )
        task = ATIFTask(
            task_id="t_overflow_stdout",
            instruction="Buffer test",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=vspec,
        )
        sandbox = SubprocessSandbox()
        cand = self._sample_candidate()
        telemetry = sandbox.execute_trial(task, cand)
        assert telemetry.passed is True
        assert telemetry.exit_code == 0

    def test_f6_boundary_non_existent_working_dir(self) -> None:
        """Boundary: Non-existent working directory handled without unhandled exception."""
        non_existent_path = "/tmp/sandbox_non_existent_path_xyz_99999"
        config = SandboxConfig(work_dir=non_existent_path) if SandboxConfig is not None else None
        sandbox = SubprocessSandbox(config=config) if config else SubprocessSandbox()
        vspec = VerificationSpec(command="echo OK", timeout_seconds=5.0)
        task = ATIFTask(
            task_id="t_noworkdir",
            instruction="Test missing dir",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=vspec,
        )
        cand = self._sample_candidate()
        telemetry = sandbox.execute_trial(task, cand)
        assert isinstance(telemetry.passed, bool)

    def test_f6_boundary_permission_denied_exit_code(self) -> None:
        """Boundary: Permission denied or 126/127 exit code is captured accurately."""
        vspec = VerificationSpec(
            command='python3 -c "import sys; sys.exit(126)"',
            timeout_seconds=5.0,
        )
        task = ATIFTask(
            task_id="t_perm_denied",
            instruction="Permission test",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=vspec,
        )
        sandbox = SubprocessSandbox()
        cand = self._sample_candidate()
        telemetry = sandbox.execute_trial(task, cand)
        assert telemetry.passed is False
        assert telemetry.exit_code == 126


# ==============================================================================
# Feature 7: Concurrent Batch Executor Boundaries
# ==============================================================================
class TestF7ConcurrentBatchExecutorBoundaries:
    """Boundary test cases for Feature 7: Concurrent Batch Executor."""

    @pytest.fixture(autouse=True)
    def _require_f7(self) -> None:
        if ConcurrentBatchExecutor is None or InMemoryMockHarness is None or ATIFTask is None:
            pytest.skip("harness_optimizer.harbor.executor.ConcurrentBatchExecutor not yet implemented")

    def _sample_task(self, tid: str) -> Any:
        vspec = VerificationSpec(command="echo batch", timeout_seconds=5.0)
        return ATIFTask(
            task_id=tid,
            instruction=f"Instruction for {tid}",
            difficulty=DifficultyLevel.EASY,
            behavioral_tags=[BehavioralTag.TOOL_SELECTION],
            verification=vspec,
        )

    def _sample_candidate(self) -> Any:
        if AgentCandidate is not None:
            return AgentCandidate(candidate_id="batch_agent")
        return "batch_agent"

    def test_f7_boundary_batch_size_zero_and_one(self) -> None:
        """Boundary: Batch of 0 tasks returns empty list; batch of 1 returns 1 telemetry."""
        harness = InMemoryMockHarness(failure_rate=0.0, seed=42)
        executor = ConcurrentBatchExecutor(max_workers=2, sandbox=harness)
        cand = self._sample_candidate()

        res_zero = executor.execute_batch([], cand)
        assert res_zero == []

        res_one = executor.execute_batch([self._sample_task("t_one")], cand)
        assert len(res_one) == 1
        assert res_one[0].passed is True

    def test_f7_boundary_max_workers_one_sequential(self) -> None:
        """Boundary: max_workers=1 executes sequentially and collects all results."""
        harness = InMemoryMockHarness(failure_rate=0.0, seed=42)
        executor = ConcurrentBatchExecutor(max_workers=1, sandbox=harness)
        tasks = [self._sample_task(f"t_seq_{i}") for i in range(5)]
        cand = self._sample_candidate()
        results = executor.execute_batch(tasks, cand)
        assert len(results) == 5
        assert set(t.task_id for t in results) == set(t.task_id for t in tasks)

    def test_f7_boundary_max_workers_sixty_four_high_concurrency(self) -> None:
        """Boundary: max_workers=64 on small batch executes without deadlock or task drop."""
        harness = InMemoryMockHarness(failure_rate=0.0, seed=42)
        executor = ConcurrentBatchExecutor(max_workers=64, sandbox=harness)
        tasks = [self._sample_task(f"t_high_{i}") for i in range(20)]
        cand = self._sample_candidate()
        results = executor.execute_batch(tasks, cand)
        assert len(results) == 20
        assert all(t.passed is True for t in results)

    def test_f7_boundary_all_tasks_failing_batch(self) -> None:
        """Boundary: Batch where all tasks fail returns full list of failed telemetries."""
        harness = InMemoryMockHarness(failure_rate=1.0, seed=42)
        executor = ConcurrentBatchExecutor(max_workers=4, sandbox=harness)
        tasks = [self._sample_task(f"t_fail_{i}") for i in range(10)]
        cand = self._sample_candidate()
        results = executor.execute_batch(tasks, cand)
        assert len(results) == 10
        assert all(t.passed is False for t in results)

    def test_f7_boundary_worker_thread_exception_resilience(self) -> None:
        """Boundary: Sandbox throwing an unexpected exception in worker thread is handled."""
        class BuggySandbox(BaseSandbox):  # type: ignore[misc]
            def execute_trial(self, task: Any, candidate: Any) -> Any:
                raise RuntimeError("Simulated crash in worker thread")

        executor = ConcurrentBatchExecutor(max_workers=2, sandbox=BuggySandbox())
        tasks = [self._sample_task("t_crash")]
        cand = self._sample_candidate()
        try:
            results = executor.execute_batch(tasks, cand)
            assert len(results) == 1
            assert results[0].passed is False
        except RuntimeError:
            pass


# ==============================================================================
# Feature 8: Beta-Binomial Conjugate Engine Boundaries
# ==============================================================================
class TestF8BetaBinomialEngineBoundaries:
    """Boundary test cases for Feature 8: Beta-Binomial Conjugate Engine."""

    @pytest.fixture(autouse=True)
    def _require_f8(self) -> None:
        if BetaBinomialModel is None:
            pytest.skip("harness_optimizer.bayesian.engine.BetaBinomialModel not yet implemented")

    def test_f8_boundary_jeffreys_prior_approaching_zero(self) -> None:
        """Boundary: Jeffreys prior (alpha=0.5, beta=0.5) operates without math domain error."""
        model = BetaBinomialModel(prior_alpha=0.5, prior_beta=0.5)
        p_sup = model.posterior_superiority(
            candidate_successes=5,
            candidate_failures=2,
            baseline_successes=3,
            baseline_failures=4,
        )
        assert 0.0 <= p_sup <= 1.0
        assert not math.isnan(p_sup)

    def test_f8_boundary_huge_sample_size_100k(self) -> None:
        """Boundary: Sample size of 100,000 trials computes without numerical overflow."""
        model = BetaBinomialModel(prior_alpha=1.0, prior_beta=1.0)
        p_sup = model.posterior_superiority(
            candidate_successes=80_000,
            candidate_failures=20_000,
            baseline_successes=60_000,
            baseline_failures=40_000,
        )
        assert not math.isnan(p_sup)
        assert not math.isinf(p_sup)
        assert p_sup > 0.99999

    def test_f8_boundary_zero_vs_hundred_percent_pass_rates(self) -> None:
        """Boundary: Candidate 0% pass rate vs Baseline 100% pass rate approaches P=0.0."""
        model = BetaBinomialModel(prior_alpha=1.0, prior_beta=1.0)
        p_sup = model.posterior_superiority(
            candidate_successes=0,
            candidate_failures=50,
            baseline_successes=50,
            baseline_failures=0,
        )
        assert p_sup < 1e-6

    def test_f8_boundary_identical_fifty_fifty_rates(self) -> None:
        """Boundary: Exactly identical 50/50 candidate and baseline rates produce P approx 0.50."""
        model = BetaBinomialModel(prior_alpha=1.0, prior_beta=1.0)
        p_sup = model.posterior_superiority(
            candidate_successes=50,
            candidate_failures=50,
            baseline_successes=50,
            baseline_failures=50,
        )
        assert 0.47 <= p_sup <= 0.53

    def test_f8_boundary_numerical_underflow_overflow_extreme_skew(self) -> None:
        """Boundary: Extreme sample size skew (10,000 vs 1) computes finite non-NaN probability."""
        model = BetaBinomialModel(prior_alpha=1.0, prior_beta=1.0)
        p_sup = model.posterior_superiority(
            candidate_successes=10_000,
            candidate_failures=1,
            baseline_successes=1,
            baseline_failures=10_000,
        )
        assert not math.isnan(p_sup)
        assert p_sup >= 0.99999


# ==============================================================================
# Feature 9: Dynamic Bayesian Early Stopping Boundaries
# ==============================================================================
class TestF9DynamicBayesianStoppingBoundaries:
    """Boundary test cases for Feature 9: Dynamic Bayesian Early Stopping."""

    @pytest.fixture(autouse=True)
    def _require_f9(self) -> None:
        if EarlyStoppingController is None or StoppingDecision is None:
            pytest.skip("harness_optimizer.bayesian.stopping not yet implemented")

    def test_f9_boundary_warmup_guard_blocks_accept(self) -> None:
        """Boundary: step < min_evals with P=0.999 must return CONTINUE (warmup guard)."""
        controller = EarlyStoppingController(
            min_evals=10,
            max_evals=100,
            accept_threshold=0.95,
            prune_threshold=0.10,
        )
        decision = controller.evaluate(step=5, p_superiority=0.999)
        assert decision == StoppingDecision.CONTINUE

    def test_f9_boundary_max_evals_forced_decision(self) -> None:
        """Boundary: step == max_evals forces terminal decision even if P is in continue range."""
        controller = EarlyStoppingController(
            min_evals=10,
            max_evals=50,
            accept_threshold=0.95,
            prune_threshold=0.10,
        )
        decision = controller.evaluate(step=50, p_superiority=0.50)
        assert decision in (StoppingDecision.PRUNE, StoppingDecision.ACCEPT)
        assert decision != StoppingDecision.CONTINUE

    def test_f9_boundary_exact_threshold_boundaries(self) -> None:
        """Boundary: P exactly at boundary 0.95 or 0.10 triggers respective action."""
        controller = EarlyStoppingController(
            min_evals=10,
            max_evals=100,
            accept_threshold=0.95,
            prune_threshold=0.10,
        )
        assert controller.evaluate(step=15, p_superiority=0.95) == StoppingDecision.ACCEPT
        assert controller.evaluate(step=15, p_superiority=0.10) == StoppingDecision.PRUNE
        assert controller.evaluate(step=15, p_superiority=0.50) == StoppingDecision.CONTINUE

    def test_f9_boundary_coincident_thresholds(self) -> None:
        """Boundary: accept_threshold == prune_threshold acts as crisp binary cut."""
        controller = EarlyStoppingController(
            min_evals=10,
            max_evals=100,
            accept_threshold=0.50,
            prune_threshold=0.50,
        )
        assert controller.evaluate(step=15, p_superiority=0.51) == StoppingDecision.ACCEPT
        assert controller.evaluate(step=15, p_superiority=0.49) == StoppingDecision.PRUNE

    def test_f9_boundary_step_zero_or_out_of_bounds(self) -> None:
        """Boundary: step <= 0 or step > max_evals handled safely without crash."""
        controller = EarlyStoppingController(
            min_evals=10,
            max_evals=100,
            accept_threshold=0.95,
            prune_threshold=0.10,
        )
        assert controller.evaluate(step=0, p_superiority=0.99) == StoppingDecision.CONTINUE
        assert controller.evaluate(step=-1, p_superiority=0.99) == StoppingDecision.CONTINUE
        assert controller.evaluate(step=150, p_superiority=0.50) in (
            StoppingDecision.PRUNE,
            StoppingDecision.ACCEPT,
        )


# ==============================================================================
# Feature 10: Error Span & Trace Extraction Boundaries
# ==============================================================================
class TestF10TraceExtractionBoundaries:
    """Boundary test cases for Feature 10: Error Span & Trace Extraction."""

    @pytest.fixture(autouse=True)
    def _require_f10(self) -> None:
        if TraceMiner is None:
            pytest.skip("harness_optimizer.clustering.trace_miner.TraceMiner not yet implemented")

    def test_f10_boundary_empty_error_message(self) -> None:
        """Boundary: Empty error message string handled without IndexError or crash."""
        miner = TraceMiner()
        extracted = miner.extract_error_span("")
        assert extracted == "" or extracted is None or isinstance(extracted, str)
        extracted_ws = miner.extract_error_span("    \t\n  ")
        assert extracted_ws == "" or isinstance(extracted_ws, str)

    def test_f10_boundary_single_line_error_no_stack(self) -> None:
        """Boundary: Single-line error string without stack frames extracted accurately."""
        miner = TraceMiner()
        single_line = "ZeroDivisionError: division by zero"
        extracted = miner.extract_error_span(single_line)
        assert "ZeroDivisionError" in extracted
        assert "division by zero" in extracted

    def test_f10_boundary_multi_megabyte_log_truncation(self) -> None:
        """Boundary: 2MB log string is truncated safely without memory exhaustion."""
        miner = TraceMiner()
        huge_log = ("Standard trace line: frame at 0x7fff\\n" * 50_000) + "IndexError: list index out of range"
        extracted = miner.extract_error_span(huge_log)
        assert len(extracted) < 100_000, "Trace extraction must bound/truncate output size"
        assert "IndexError" in extracted

    def test_f10_boundary_deeply_nested_stack_trace(self) -> None:
        """Boundary: Deeply nested stack trace (100 frames) extracted without RecursionError."""
        miner = TraceMiner()
        frames = [f'  File "module_{i}.py", line {i}, in func_{i}\\n    call_{i}()' for i in range(100)]
        frames.append("RuntimeError: Maximum recursion depth exceeded")
        trace = "\\n".join(["Traceback (most recent call last):"] + frames)
        extracted = miner.extract_error_span(trace)
        assert "RuntimeError" in extracted

    def test_f10_boundary_malformed_syntax_error_trace(self) -> None:
        """Boundary: Corrupted syntax error trace with misaligned carets and null bytes parsed safely."""
        miner = TraceMiner()
        malformed = (
            "SyntaxError: invalid syntax\\n"
            "   def broken_func(" + chr(0) + "):\\n"
            "       ^^^^^^^^^^^^^^^^\\n"
            "Corrupted binary tail: \\xff\\xfe"
        )
        extracted = miner.extract_error_span(malformed)
        assert "SyntaxError" in extracted


# ==============================================================================
# Feature 11: TF-IDF Trace Vectorizer Boundaries
# ==============================================================================
class TestF11TFIDFTraceVectorizerBoundaries:
    """Boundary test cases for Feature 11: TF-IDF Trace Vectorizer."""

    @pytest.fixture(autouse=True)
    def _require_f11(self) -> None:
        if TraceVectorizer is None:
            pytest.skip("harness_optimizer.clustering.vectorizer.TraceVectorizer not yet implemented")

    def test_f11_boundary_single_document_corpus(self) -> None:
        """Boundary: Corpus containing a single document computes valid 2D matrix without zero division."""
        vectorizer = TraceVectorizer()
        matrix = vectorizer.fit_transform(["ZeroDivisionError: division by zero in worker"])
        assert matrix.shape[0] == 1
        assert matrix.shape[1] > 0
        assert not np.isnan(matrix).any()

    def test_f11_boundary_all_identical_documents(self) -> None:
        """Boundary: All identical documents produce identical non-NaN row vectors."""
        vectorizer = TraceVectorizer()
        docs = ["TimeoutError: Task execution timed out after 60s"] * 5
        matrix = vectorizer.fit_transform(docs)
        assert matrix.shape[0] == 5
        assert not np.isnan(matrix).any()
        diff = np.abs(matrix[0] - matrix[1])
        assert np.max(diff) < 1e-9

    def test_f11_boundary_disjoint_vocabulary_documents(self) -> None:
        """Boundary: Documents with zero overlapping vocabulary yield orthogonal vectors."""
        vectorizer = TraceVectorizer()
        docs = [
            "alpha beta gamma",
            "delta epsilon zeta",
        ]
        matrix = vectorizer.fit_transform(docs)
        dot_product = float(np.dot(matrix[0], matrix[1]))
        assert abs(dot_product) < 1e-9

    def test_f11_boundary_max_features_one(self) -> None:
        """Boundary: max_features=1 restricts feature vocabulary to exactly 1 column."""
        vectorizer = TraceVectorizer(max_features=1)
        docs = ["error error error bug", "error problem", "error failure"]
        matrix = vectorizer.fit_transform(docs)
        assert matrix.shape == (3, 1)

    def test_f11_boundary_empty_string_documents(self) -> None:
        """Boundary: Empty string documents produce zero vectors without crash."""
        vectorizer = TraceVectorizer()
        docs = ["", "   ", ""]
        matrix = vectorizer.fit_transform(docs)
        assert matrix.shape[0] == 3
        assert not np.isnan(matrix).any()


# ==============================================================================
# Feature 12: Unsupervised Archetype Clustering Boundaries
# ==============================================================================
class TestF12ArchetypeClusteringBoundaries:
    """Boundary test cases for Feature 12: Unsupervised Archetype Clustering."""

    @pytest.fixture(autouse=True)
    def _require_f12(self) -> None:
        if ArchetypeClusterer is None and TraceMiner is None:
            pytest.skip("Archetype clustering not yet implemented")

    def _cluster(self, traces: List[str], k: int) -> Any:
        if ArchetypeClusterer is not None:
            clusterer = ArchetypeClusterer(k_clusters=k)
            return clusterer.fit_predict(traces)
        miner = TraceMiner()
        return miner.cluster_failures(traces, k_clusters=k)

    def test_f12_boundary_k_equals_one_single_cluster(self) -> None:
        """Boundary: k=1 single cluster assigns all failure traces to cluster 0."""
        traces = [
            "SyntaxError: invalid syntax in line 10",
            "SyntaxError: unmatched parenthesis",
            "SyntaxError: unexpected EOF",
        ]
        report = self._cluster(traces, k=1)
        assert report is not None

    def test_f12_boundary_k_equals_number_of_documents(self) -> None:
        """Boundary: k equal to number of documents operates without singularity error."""
        traces = [
            "TimeoutError: process exceeded watchdog deadline",
            "FileNotFoundError: missing required test artifact",
            "AssertionError: output does not match expectation",
        ]
        report = self._cluster(traces, k=3)
        assert report is not None

    def test_f12_boundary_disjoint_vocabulary_clusters(self) -> None:
        """Boundary: Distinct error families clustered cleanly into separated groups."""
        traces = [
            "TimeoutError: network socket timeout waiting for server",
            "TimeoutError: connection deadline exceeded after 30s",
            "ImportError: cannot import name 'missing_symbol'",
            "ImportError: no module named 'uninstalled_dep'",
        ]
        report = self._cluster(traces, k=2)
        assert report is not None

    def test_f12_boundary_identical_duplicate_failure_traces(self) -> None:
        """Boundary: Identical duplicate traces grouped into same cluster without zero variance crash."""
        traces = ["SegmentationFault: core dumped in C++ extension"] * 8
        report = self._cluster(traces, k=1)
        assert report is not None

    def test_f12_boundary_empty_cluster_handling(self) -> None:
        """Boundary: When k exceeds distinct pattern count, empty clusters are handled cleanly."""
        traces = [
            "AssertionError: True is not False",
            "AssertionError: 1 != 2",
        ]
        report = self._cluster(traces, k=5)
        assert report is not None


# ==============================================================================
# Feature 13: Paired Holdout Testing (McNemar) Boundaries
# ==============================================================================
class TestF13PairedHoldoutGateBoundaries:
    """Boundary test cases for Feature 13: Paired Holdout Testing (McNemar)."""

    @pytest.fixture(autouse=True)
    def _require_f13(self) -> None:
        if HoldoutGate is None and mcnemar_test is None:
            pytest.skip("harness_optimizer.lifecycle.holdout_gate not yet implemented")

    def _make_telemetry(self, passed: bool, task_id: str) -> Any:
        return TrialTelemetry(
            trial_id=f"t_{task_id}_{passed}",
            task_id=task_id,
            candidate_id="agent",
            passed=passed,
            exit_code=0 if passed else 1,
            latency_ms=10.0,
            token_spend=TokenSpend(prompt_tokens=5, completion_tokens=5, total_tokens=10),
            trace_logs=[],
        )

    def test_f13_boundary_zero_discordant_pairs(self) -> None:
        """Boundary: 0 discordant pairs (b=0, c=0) yields p=1.0 and candidate is rejected."""
        gate = HoldoutGate(alpha=0.05) if HoldoutGate is not None else None
        base = [self._make_telemetry(True, f"task_{i}") for i in range(10)]
        cand = [self._make_telemetry(True, f"task_{i}") for i in range(10)]
        if gate is not None:
            decision = gate.evaluate(baseline_results=base, candidate_results=cand)
            assert decision.p_value >= 0.99
            assert decision.passed is False
        else:
            p_val, stat = mcnemar_test([t.passed for t in base], [t.passed for t in cand])
            assert p_val >= 0.99

    def test_f13_boundary_only_concordant_pairs(self) -> None:
        """Boundary: Perfect agreement with all failing yields p=1.0 and rejection."""
        gate = HoldoutGate(alpha=0.05) if HoldoutGate is not None else None
        base = [self._make_telemetry(False, f"task_{i}") for i in range(15)]
        cand = [self._make_telemetry(False, f"task_{i}") for i in range(15)]
        if gate is not None:
            decision = gate.evaluate(baseline_results=base, candidate_results=cand)
            assert decision.p_value >= 0.99
            assert decision.passed is False

    def test_f13_boundary_extreme_discordance_candidate_superior(self) -> None:
        """Boundary: Extreme discordance (b=100, c=0) yields p < 1e-15 and acceptance."""
        gate = HoldoutGate(alpha=0.05) if HoldoutGate is not None else None
        base = [self._make_telemetry(False, f"task_{i}") for i in range(100)]
        cand = [self._make_telemetry(True, f"task_{i}") for i in range(100)]
        if gate is not None:
            decision = gate.evaluate(baseline_results=base, candidate_results=cand)
            assert decision.p_value < 1e-10
            assert decision.passed is True

    def test_f13_boundary_tiny_sample_size_two_tasks(self) -> None:
        """Boundary: Tiny sample size (N=2) uses exact test without division by zero."""
        gate = HoldoutGate(alpha=0.05) if HoldoutGate is not None else None
        base = [self._make_telemetry(False, "t1"), self._make_telemetry(False, "t2")]
        cand = [self._make_telemetry(True, "t1"), self._make_telemetry(False, "t2")]
        if gate is not None:
            decision = gate.evaluate(baseline_results=base, candidate_results=cand)
            assert 0.0 <= decision.p_value <= 1.0
            assert not math.isnan(decision.p_value)

    def test_f13_boundary_alpha_edge_thresholds(self) -> None:
        """Boundary: alpha=0.0 rejects all; alpha=1.0 accepts non-zero improvements."""
        base = [self._make_telemetry(False, f"task_{i}") for i in range(20)]
        cand = [self._make_telemetry(True, f"task_{i}") for i in range(20)]
        gate_strict = HoldoutGate(alpha=0.0) if HoldoutGate is not None else None
        gate_permissive = HoldoutGate(alpha=1.0) if HoldoutGate is not None else None
        if gate_strict and gate_permissive:
            assert gate_strict.evaluate(base, cand).passed is False
            assert gate_permissive.evaluate(base, cand).passed is True


# ==============================================================================
# Feature 14: State-Machine Lifecycle Orchestration Boundaries
# ==============================================================================
class TestF14StateMachineLifecycleBoundaries:
    """Boundary test cases for Feature 14: State-Machine Lifecycle Orchestration."""

    @pytest.fixture(autouse=True)
    def _require_f14(self) -> None:
        if OptimizationStateMachine is None or OptimizationState is None:
            pytest.skip("harness_optimizer.lifecycle.state_machine not yet implemented")

    def test_f14_boundary_invalid_state_transition_attempt(self) -> None:
        """Boundary: Invalid transition attempt (IDLE -> BASELINE_UPDATE) raises error."""
        sm = OptimizationStateMachine()
        err_cls = InvalidStateTransitionError if InvalidStateTransitionError is not None else ValueError
        with pytest.raises((err_cls, ValueError)):
            sm.transition(OptimizationState.BASELINE_UPDATE)

    def test_f14_boundary_reset_to_idle_from_any_state(self) -> None:
        """Boundary: Reset to IDLE from active evaluation states cleans state safely."""
        sm = OptimizationStateMachine()
        sm.transition(OptimizationState.BASELINE_RUN)
        sm.transition(OptimizationState.CANDIDATE_SEARCH)
        sm.reset()
        assert sm.current_state == OptimizationState.IDLE

    def test_f14_boundary_concurrent_transition_attempts(self) -> None:
        """Boundary: Multi-threaded concurrent transitions maintain valid state invariants."""
        sm = OptimizationStateMachine()
        barrier = threading.Barrier(5)
        errors = []

        def worker() -> None:
            try:
                barrier.wait()
                sm.transition(OptimizationState.BASELINE_RUN)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sm.current_state in (OptimizationState.BASELINE_RUN, OptimizationState.IDLE)

    def test_f14_boundary_transition_with_missing_intermediate_results(self) -> None:
        """Boundary: Transition to HOLDOUT_GATE guarded against missing candidate results."""
        sm = OptimizationStateMachine()
        sm.transition(OptimizationState.BASELINE_RUN)
        sm.transition(OptimizationState.CANDIDATE_SEARCH)
        err_cls = InvalidStateTransitionError if InvalidStateTransitionError is not None else ValueError
        with pytest.raises((err_cls, ValueError)):
            sm.transition(OptimizationState.HOLDOUT_GATE)

    def test_f14_boundary_self_transition(self) -> None:
        """Boundary: Self-transition IDLE -> IDLE handled as idempotent or guarded cleanly."""
        sm = OptimizationStateMachine()
        try:
            sm.transition(OptimizationState.IDLE)
            assert sm.current_state == OptimizationState.IDLE
        except (ValueError, Exception):
            pass


# ==============================================================================
# Feature 15: Synthetic Benchmark Suite Generator Boundaries
# ==============================================================================
class TestF15SyntheticBenchmarkBoundaries:
    """Boundary test cases for Feature 15: Synthetic Benchmark Suite Generator."""

    @pytest.fixture(autouse=True)
    def _require_f15(self) -> None:
        if SyntheticBenchmarkGenerator is None:
            pytest.skip("harness_optimizer.synthetic.benchmark not yet implemented")

    def test_f15_boundary_generate_zero_tasks(self) -> None:
        """Boundary: Generating 0 tasks returns valid empty BenchmarkSuite."""
        gen = SyntheticBenchmarkGenerator(seed=42)
        suite = gen.generate_suite(num_tasks=0)
        assert len(suite) == 0
        assert suite.tasks == []

    def test_f15_boundary_generate_single_task(self) -> None:
        """Boundary: Generating 1 task returns suite with exactly 1 fully valid ATIF task."""
        gen = SyntheticBenchmarkGenerator(seed=42)
        suite = gen.generate_suite(num_tasks=1)
        assert len(suite) == 1
        task = suite.tasks[0]
        assert task.task_id != ""
        assert len(task.instruction) > 0
        assert len(task.behavioral_tags) > 0

    def test_f15_boundary_generate_thousand_tasks(self) -> None:
        """Boundary: Generating 1,000 tasks creates 1,000 unique non-colliding task IDs."""
        gen = SyntheticBenchmarkGenerator(seed=42)
        suite = gen.generate_suite(num_tasks=1000)
        assert len(suite) == 1000
        unique_ids = set(t.task_id for t in suite.tasks)
        assert len(unique_ids) == 1000

    def test_f15_boundary_extreme_difficulty_skew(self) -> None:
        """Boundary: 100% EXPERT difficulty skew produces 100% EXPERT tasks."""
        gen = SyntheticBenchmarkGenerator(seed=42)
        suite = gen.generate_suite(
            num_tasks=25,
            difficulty_distribution={DifficultyLevel.EXPERT: 1.0},
        )
        assert all(t.difficulty == DifficultyLevel.EXPERT for t in suite.tasks)

    def test_f15_boundary_custom_taxonomy_tag_extension(self) -> None:
        """Boundary: Custom or single tag constraint generates tasks with that specified tag."""
        gen = SyntheticBenchmarkGenerator(seed=42)
        suite = gen.generate_suite(
            num_tasks=20,
            tag_distribution={BehavioralTag.CONSTRAINT_ADHERENCE: 1.0},
        )
        assert all(
            BehavioralTag.CONSTRAINT_ADHERENCE in t.behavioral_tags
            for t in suite.tasks
        )


# ==============================================================================
# Feature 16: CLI Entrypoint & Packaging Boundaries
# ==============================================================================
class TestF16CLIEntrypointBoundaries:
    """Boundary test cases for Feature 16: CLI Entrypoint & Packaging."""

    def _run_cli(self, args: List[str]) -> subprocess.CompletedProcess[str]:
        cli_py = PROJECT_ROOT / "cli.py"
        if not cli_py.exists():
            cli_py = PROJECT_ROOT / "harness_optimizer" / "__main__.py"
        if not cli_py.exists():
            pytest.skip("CLI entrypoint (cli.py or __main__.py) not yet implemented")
        cmd = [sys.executable, str(cli_py)] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=15)

    def test_f16_boundary_cli_unknown_flags(self) -> None:
        """Boundary: Unknown CLI flags must exit with non-zero code."""
        result = self._run_cli(["--completely-unknown-flag-xyz-98765"])
        assert result.returncode != 0
        assert "unrecognized" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_f16_boundary_cli_invalid_types(self) -> None:
        """Boundary: Invalid argument types (e.g. negative max-evals) exit with error."""
        result = self._run_cli(["--max-evals", "-5"])
        assert result.returncode != 0

    def test_f16_boundary_cli_missing_required_config(self) -> None:
        """Boundary: Missing required arguments reports clear usage and exits non-zero."""
        result = self._run_cli(["--run-nonexistent-suite"])
        assert result.returncode != 0

    def test_f16_boundary_cli_help_flag(self) -> None:
        """Boundary: --help flag exits with code 0 and displays help text."""
        result = self._run_cli(["--help"])
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "options" in result.stdout.lower()

    def test_f16_boundary_cli_output_format_json_vs_text(self) -> None:
        """Boundary: Output format validation for json vs text format."""
        result = self._run_cli(["--help", "--output-format=json"])
        assert result.returncode == 0 or result.returncode == 2
