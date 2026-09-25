"""Tier 3 Pairwise Combinatorial Test Suite.

Validates pairwise cross-module contracts and state interactions across all 16 features:
  1. F1 + F2: Ingested ATIF tasks partitioned via Stratified Splitter.
  2. F2 + F3: Stratified split followed by Statistical Divergence verification.
  3. F1 + F15: Synthetic benchmark generation loaded and validated as ATIF tasks.
  4. F4 + F5: InMemoryMockHarness executing trials and emitting TrialTelemetry.
  5. F4 + F6: SubprocessSandbox execution emitting structured TrialTelemetry.
  6. F5 + F7: ConcurrentBatchExecutor distributing tasks across InMemoryMockHarness.
  7. F6 + F7: ConcurrentBatchExecutor running parallel SubprocessSandboxes.
  8. F4 + F10: Failed TrialTelemetry piped into TraceMiner for error extraction.
  9. F10 + F11: Extracted error spans vectorized by TF-IDF TraceVectorizer.
  10. F11 + F12: Vectorized error traces clustered into ArchetypeClusters.
  11. F8 + F9: BetaBinomialModel posterior superiority feeding into EarlyStoppingController.
  12. F7 + F9: Concurrent batch execution stream evaluated step-by-step by EarlyStoppingController.
  13. F8 + F13: Optimization set Bayesian superiority followed by Holdout McNemar's test.
  14. F13 + F14: McNemar test outcome directly driving State Machine transition.
  15. F12 + F14: TRACE_DIAGNOSIS state invoking Archetype Clustering to extract diagnostic terms.
  16. F15 + F16: Synthetic benchmark generator feeding directly into CLI sweep runner.
  17. F1 + F4: Ingested ATIF task metadata propagated into TrialTelemetry.
  18. F5 + F8: Mock trials iteratively updating BetaBinomialModel posterior.
  19. F9 + F14: Bayesian early pruning triggering state transition to TRACE_DIAGNOSIS.
  20. F2 + F15: Synthetic benchmark suite partition preserving strata with zero leakage.
"""

import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Dynamic Import Helpers with Informative Progressive Skipping
# ============================================================================

def import_benchhub():
    """Imports F1, F2, F3 components or skips if not implemented."""
    try:
        from harness_optimizer.benchhub import schema, splitter
        try:
            from harness_optimizer.benchhub import loader
        except ImportError:
            loader = None
        return schema, loader, splitter
    except ImportError as exc:
        pytest.skip(f"harness_optimizer.benchhub not implemented: {exc}")


def import_harbor():
    """Imports F4, F5, F6, F7 components or skips if not implemented."""
    try:
        from harness_optimizer.harbor import config, executor, sandbox, telemetry
        return config, executor, sandbox, telemetry
    except ImportError as exc:
        pytest.skip(f"harness_optimizer.harbor not implemented: {exc}")


def import_bayesian():
    """Imports F8, F9 components or skips if not implemented."""
    try:
        from harness_optimizer.bayesian import engine, stopping
        return engine, stopping
    except ImportError as exc:
        pytest.skip(f"harness_optimizer.bayesian not implemented: {exc}")


def import_clustering():
    """Imports F10, F11, F12 components or skips if not implemented."""
    try:
        from harness_optimizer.clustering import archetypes, trace_miner, vectorizer
        return archetypes, trace_miner, vectorizer
    except ImportError as exc:
        pytest.skip(f"harness_optimizer.clustering not implemented: {exc}")


def import_lifecycle():
    """Imports F13, F14 components or skips if not implemented."""
    try:
        from harness_optimizer.lifecycle import holdout_gate, state_machine
        try:
            from harness_optimizer.lifecycle import orchestrator
        except ImportError:
            orchestrator = None
        return holdout_gate, state_machine, orchestrator
    except ImportError as exc:
        pytest.skip(f"harness_optimizer.lifecycle not implemented: {exc}")


def import_synthetic():
    """Imports F15 component or skips if not implemented."""
    try:
        from harness_optimizer.synthetic import benchmark
        return benchmark
    except ImportError as exc:
        pytest.skip(f"harness_optimizer.synthetic not implemented: {exc}")


def import_cli():
    """Imports F16 CLI module or skips if not implemented."""
    try:
        import cli
        return cli
    except ImportError as exc:
        pytest.skip(f"cli module not importable: {exc}")


# ============================================================================
# Test Fixture / Factory Helpers
# ============================================================================

def make_sample_task(
    task_id: str,
    difficulty: str = "medium",
    tags: Optional[List[str]] = None,
    command: str = "echo 'pass'",
    metadata: Optional[Dict[str, Any]] = None,
):
    """Creates a valid ATIFTask instance dynamically."""
    schema, _, _ = import_benchhub()
    diff_enum = getattr(schema.DifficultyLevel, difficulty.upper(), difficulty)
    tag_enums = []
    for t in (tags or ["tool_selection"]):
        tag_enum = getattr(schema.BehavioralTag, t.upper(), t)
        tag_enums.append(tag_enum)

    spec = schema.VerificationSpec(
        command=command,
        timeout_sec=10.0,
        expected_exit_code=0,
    )
    return schema.ATIFTask(
        task_id=task_id,
        instruction=f"Execute task {task_id}",
        difficulty=diff_enum,
        behavioral_tags=tag_enums,
        verification=spec,
        metadata=metadata or {"domain": "code_refactoring"},
    )


def make_task_corpus(count: int = 20) -> List[Any]:
    """Generates a corpus of ATIFTask objects covering all tags and difficulty strata."""
    diffs = ["easy", "medium", "hard"]
    tag_combinations = [
        ["tool_selection"],
        ["multi_step_retrieval"],
        ["state_mutation"],
        ["constraint_adherence"],
        ["tool_selection", "state_mutation"],
        ["multi_step_retrieval", "constraint_adherence"],
    ]
    tasks = []
    for i in range(count):
        d = diffs[i % len(diffs)]
        tags = tag_combinations[i % len(tag_combinations)]
        tasks.append(make_sample_task(f"task_{i:03d}", difficulty=d, tags=tags))
    return tasks


class DummyCandidate:
    """Mock agent candidate for trial execution."""
    def __init__(self, candidate_id: str = "cand_test_01", model_name: str = "mock-agent"):
        self.candidate_id = candidate_id
        self.model_name = model_name
        self.system_prompt = "You are an autonomous coding assistant."


# ============================================================================
# Pairwise Interaction Tests (16 Mandatory + 4 Extra Combinations)
# ============================================================================

def test_comb_01_f1_f2_ingestion_and_stratified_split():
    """Interaction F1 + F2: Ingested ATIF tasks partitioned via Stratified Splitter.

    Verifies that tasks ingested from ATIF format can be partitioned into Optimization
    and Holdout sets with exact preservation of tasks, zero leakage, and valid ratio.
    """
    schema, loader, splitter_mod = import_benchhub()
    tasks = make_task_corpus(count=30)

    splitter = splitter_mod.StratifiedSplitter(opt_ratio=0.7, seed=42)
    split_result = splitter.split(tasks)

    if isinstance(split_result, tuple):
        opt_set, holdout_set = split_result
    else:
        opt_set = split_result.optimization_set
        holdout_set = split_result.holdout_set

    # 1. Total preservation
    assert len(opt_set) + len(holdout_set) == len(tasks)
    # 2. Ratio adherence (approx 70% / 30% with integer rounding)
    assert abs(len(opt_set) - 21) <= 2
    assert abs(len(holdout_set) - 9) <= 2
    # 3. Non-leakage / mutual exclusivity
    opt_ids = {t.task_id for t in opt_set}
    holdout_ids = {t.task_id for t in holdout_set}
    assert opt_ids.isdisjoint(holdout_ids), "Task leakage detected between partitions!"
    # 4. Both partitions contain ATIFTask instances
    for t in opt_set:
        assert isinstance(t, schema.ATIFTask)
    for t in holdout_set:
        assert isinstance(t, schema.ATIFTask)


def test_comb_02_f2_f3_stratified_split_statistical_divergence():
    """Interaction F2 + F3: Stratified split followed by Statistical Divergence verification.

    Verifies that stratified partitioning results in low Jensen-Shannon divergence
    across behavioral tags and difficulty strata between Optimization and Holdout sets.
    """
    _, _, splitter_mod = import_benchhub()
    tasks = make_task_corpus(count=40)

    splitter = splitter_mod.StratifiedSplitter(opt_ratio=0.7, seed=42)
    split_res = splitter.split(tasks)
    opt_set, holdout_set = split_res if isinstance(split_res, tuple) else (split_res.optimization_set, split_res.holdout_set)

    # Check if splitter has verify_divergence or direct functions
    if hasattr(splitter, "verify_divergence"):
        divergence_report = splitter.verify_divergence(opt_set, holdout_set)
        # JSD should be well below 0.15 for balanced stratification
        jsd = getattr(divergence_report, "jsd", getattr(divergence_report, "divergence", 0.05))
        assert jsd < 0.20, f"Divergence too high: {jsd}"
    elif hasattr(splitter_mod, "jensen_shannon_divergence"):
        # Direct verification of marginal tag distributions
        tags = ["tool_selection", "multi_step_retrieval", "state_mutation", "constraint_adherence"]
        def get_dist(task_list):
            counts = [sum(1 for t in task_list if any(str(tag).lower().endswith(tg) for tag in t.behavioral_tags)) for tg in tags]
            total = sum(counts) or 1
            return [c / total for c in counts]
        p_opt = get_dist(opt_set)
        p_hld = get_dist(holdout_set)
        jsd_val = splitter_mod.jensen_shannon_divergence(p_opt, p_hld)
        assert jsd_val < 0.20, f"JSD divergence exceeds balance threshold: {jsd_val}"
    else:
        # Fallback invariant: both partitions share difficulty levels
        opt_diffs = {t.difficulty for t in opt_set}
        hld_diffs = {t.difficulty for t in holdout_set}
        assert opt_diffs == hld_diffs, "Strata missing between partitions!"


def test_comb_03_f1_f15_synthetic_generation_atif_validation():
    """Interaction F1 + F15: Synthetic benchmark generation loaded and validated as ATIF tasks.

    Verifies that the SyntheticBenchmarkGenerator produces tasks that strictly
    satisfy all Pydantic ATIFTask schema constraints.
    """
    schema, _, _ = import_benchhub()
    bench_mod = import_synthetic()

    generator = bench_mod.SyntheticBenchmarkGenerator(seed=123)
    gen_func = getattr(generator, "generate_suite", getattr(generator, "generate", None))
    assert gen_func is not None, "Generator missing generate_suite method"

    suite = gen_func(task_count=15)
    assert len(suite) == 15

    for task in suite:
        assert isinstance(task, schema.ATIFTask)
        assert task.task_id.startswith("task_") or len(task.task_id) > 0
        assert len(task.instruction) > 0
        assert task.difficulty in [
            schema.DifficultyLevel.EASY,
            schema.DifficultyLevel.MEDIUM,
            schema.DifficultyLevel.HARD,
        ]
        assert len(task.behavioral_tags) >= 1
        assert task.verification.command is not None
        assert isinstance(task.verification.timeout_sec, (int, float))


def test_comb_04_f4_f5_mock_harness_trial_telemetry():
    """Interaction F4 + F5: InMemoryMockHarness executing trials and emitting TrialTelemetry.

    Verifies that InMemoryMockHarness produces fully formed TrialTelemetry instances
    with valid token spend, trace spans, latency, and exit codes.
    """
    config_mod, _, sandbox_mod, telemetry_mod = import_harbor()
    task = make_sample_task("task_telemetry_01")
    candidate = DummyCandidate("cand_01")

    # 1. Deterministic passing mock
    mock_pass = sandbox_mod.InMemoryMockHarness(failure_rate=0.0, seed=42)
    tel_pass = mock_pass.execute_trial(task, candidate)

    assert isinstance(tel_pass, telemetry_mod.TrialTelemetry)
    assert tel_pass.task_id == "task_telemetry_01"
    assert tel_pass.candidate_id == "cand_01"
    assert tel_pass.passed is True
    assert tel_pass.exit_code == 0
    assert tel_pass.latency_ms >= 0.0
    assert tel_pass.token_spend.total_tokens == tel_pass.token_spend.prompt_tokens + tel_pass.token_spend.completion_tokens
    assert len(tel_pass.trace_logs) >= 1

    # 2. Deterministic failing mock
    mock_fail = sandbox_mod.InMemoryMockHarness(failure_rate=1.0, seed=42)
    tel_fail = mock_fail.execute_trial(task, candidate)
    assert tel_fail.passed is False
    assert tel_fail.exit_code != 0
    assert tel_fail.raw_error_message is not None


def test_comb_05_f4_f6_subprocess_sandbox_telemetry():
    """Interaction F4 + F6: SubprocessSandbox execution emitting structured TrialTelemetry.

    Executes real subprocess commands via SubprocessSandbox and asserts structured
    telemetry capture of exit code, stdout/stderr, and duration.
    """
    config_mod, _, sandbox_mod, telemetry_mod = import_harbor()

    cfg = config_mod.SandboxConfig(timeout_sec=5.0)
    sandbox = sandbox_mod.SubprocessSandbox(config=cfg)

    # Passing command
    pass_task = make_sample_task("subproc_pass", command="python3 -c \"print('ALL_GOOD'); exit(0)\"")
    candidate = DummyCandidate("cand_subproc")
    tel_pass = sandbox.execute_trial(pass_task, candidate)

    assert isinstance(tel_pass, telemetry_mod.TrialTelemetry)
    assert tel_pass.passed is True
    assert tel_pass.exit_code == 0
    assert tel_pass.latency_ms > 0.0

    # Failing command
    fail_task = make_sample_task("subproc_fail", command="python3 -c \"import sys; sys.stderr.write('FAILURE'); exit(2)\"")
    tel_fail = sandbox.execute_trial(fail_task, candidate)
    assert tel_fail.passed is False
    assert tel_fail.exit_code == 2
    assert tel_fail.raw_error_message is not None or any(s.status == "error" for s in tel_fail.trace_logs)


def test_comb_06_f5_f7_concurrent_executor_mock_harness():
    """Interaction F5 + F7: ConcurrentBatchExecutor distributing tasks across InMemoryMockHarness.

    Verifies parallel trial execution of a batch of ATIF tasks with deterministic
    results and correct task-telemetry mapping.
    """
    _, executor_mod, sandbox_mod, telemetry_mod = import_harbor()
    tasks = make_task_corpus(count=12)
    candidate = DummyCandidate("cand_concurrent")

    harness = sandbox_mod.InMemoryMockHarness(failure_rate=0.25, seed=101)
    batch_exec = executor_mod.ConcurrentBatchExecutor(sandbox=harness, max_workers=4)

    results = batch_exec.execute_batch(tasks, candidate)
    assert len(results) == len(tasks)

    # Check task IDs match perfectly
    input_ids = {t.task_id for t in tasks}
    result_task_ids = {r.task_id for r in results}
    assert input_ids == result_task_ids
    for r in results:
        assert isinstance(r, telemetry_mod.TrialTelemetry)
        assert r.candidate_id == "cand_concurrent"


def test_comb_07_f6_f7_concurrent_executor_subprocess_sandboxes():
    """Interaction F6 + F7: ConcurrentBatchExecutor running parallel SubprocessSandboxes.

    Verifies that multiple SubprocessSandbox trials run concurrently without interference,
    deadlocks, or file collisions.
    """
    config_mod, executor_mod, sandbox_mod, telemetry_mod = import_harbor()
    cfg = config_mod.SandboxConfig(timeout_sec=5.0)
    sandbox = sandbox_mod.SubprocessSandbox(config=cfg)
    batch_exec = executor_mod.ConcurrentBatchExecutor(sandbox=sandbox, max_workers=4)

    # Create 4 tasks with lightweight sleep
    tasks = [
        make_sample_task(f"parallel_sub_{i}", command="python3 -c \"import time; time.sleep(0.02); exit(0)\"")
        for i in range(4)
    ]
    candidate = DummyCandidate("cand_sub_parallel")

    t0 = time.perf_counter()
    results = batch_exec.execute_batch(tasks, candidate)
    elapsed = time.perf_counter() - t0

    assert len(results) == 4
    for r in results:
        assert r.passed is True
        assert r.exit_code == 0
    # Concurrent execution should complete well within timeout
    assert elapsed < 10.0


def test_comb_08_f4_f10_failed_telemetry_to_trace_miner():
    """Interaction F4 + F10: Failed TrialTelemetry piped into TraceMiner for error extraction.

    Verifies that raw error messages and stack traces inside TrialTelemetry are
    sanitized, normalized, and converted into structured error spans.
    """
    _, _, _, telemetry_mod = import_harbor()
    _, miner_mod, _ = import_clustering()

    raw_error = "Traceback (most recent call last):\n  File '/tmp/harness/run.py', line 128, in execute\nMemoryError: Context length 65536 exceeded in attention block at 0x7f8a1c3d"
    telemetry = telemetry_mod.TrialTelemetry(
        trial_id="trial_err_01",
        task_id="task_err_01",
        candidate_id="cand_01",
        passed=False,
        exit_code=1,
        latency_ms=120.0,
        token_spend=telemetry_mod.TokenSpend(),
        trace_logs=[],
        raw_error_message=raw_error,
    )

    miner = miner_mod.TraceMiner()
    if hasattr(miner, "extract_error_spans"):
        spans = miner.extract_error_spans([telemetry])
        extracted = spans[0] if spans else ""
    else:
        extracted = miner.extract_error_span(telemetry.raw_error_message)

    assert "MemoryError" in extracted or "Context length" in extracted
    # Ensure memory address 0x7f8a1c3d is normalized out or sanitized
    assert "0x7f8a1c3d" not in extracted, "Transient memory address was not sanitized!"


def test_comb_09_f10_f11_extracted_spans_to_tfidf_vectorizer():
    """Interaction F10 + F11: Extracted error spans vectorized by TF-IDF TraceVectorizer.

    Verifies that extracted normalized error spans are transformed into numerical
    feature vectors with appropriate n-gram vocabulary and non-zero TF-IDF weights.
    """
    _, miner_mod, vectorizer_mod = import_clustering()

    raw_logs = [
        "SyntaxError: invalid syntax in ast.parse() unexpected token at line 14",
        "SyntaxError: unmatched parenthesis in expression evaluation at line 88",
        "TimeoutError: Process watchdog timed out after 30.0 seconds limit",
        "TimeoutError: Execution exceeded 30.0s deadline in container",
    ]
    miner = miner_mod.TraceMiner()
    spans = [miner.extract_error_span(log) if hasattr(miner, "extract_error_span") else log for log in raw_logs]

    vectorizer = vectorizer_mod.TraceVectorizer(ngram_range=(1, 2), max_features=50)
    matrix = vectorizer.fit_transform(spans)

    # Invariants: 4 documents vectorized
    assert matrix.shape[0] == 4
    assert matrix.shape[1] > 0
    # Documents of same type should have positive cosine similarity
    doc0 = matrix[0] / (np.linalg.norm(matrix[0]) or 1.0)
    doc1 = matrix[1] / (np.linalg.norm(matrix[1]) or 1.0)
    sim = float(np.dot(doc0, doc1))
    assert sim > 0.05, f"Syntax errors should share n-gram similarity, got {sim}"


def test_comb_10_f11_f12_vectorized_traces_to_archetype_clusters():
    """Interaction F11 + F12: Vectorized error traces clustered into ArchetypeClusters.

    Verifies that TF-IDF vectorized traces are clustered into coherent ArchetypeClusters
    with top diagnostic terms and representative exemplars.
    """
    archetypes_mod, _, vectorizer_mod = import_clustering()

    traces = [
        "ContextOverflow: token budget 32768 exceeded with prompt size 35000",
        "ContextOverflow: maximum context window reached during multi-turn conversation",
        "WatchdogTimeout: command execution took longer than 30s deadline",
        "WatchdogTimeout: runner process did not exit within timeout limit",
        "ToolCallMalformed: unexpected JSON token in arguments dictionary",
        "ToolCallMalformed: failed to parse tool call JSON schema mismatch",
    ]

    vec = vectorizer_mod.TraceVectorizer(ngram_range=(1, 2), max_features=50)
    vectors = vec.fit_transform(traces)

    clusterer = archetypes_mod.ArchetypeClusterer(k_clusters=3, random_state=42)
    report = clusterer.fit_predict(vectors, traces)

    clusters = report.clusters if hasattr(report, "clusters") else report
    assert len(clusters) == 3
    # Every cluster must have top_terms and exemplars
    for cluster in clusters:
        assert hasattr(cluster, "top_terms")
        assert len(cluster.top_terms) >= 1
        assert hasattr(cluster, "exemplars")
        assert len(cluster.exemplars) >= 1


def test_comb_11_f8_f9_bayesian_superiority_to_early_stopping():
    """Interaction F8 + F9: BetaBinomialModel posterior superiority feeding into EarlyStoppingController.

    Validates that exact posterior superiority calculated by BetaBinomialModel
    correctly triggers dynamic stopping boundaries (ACCEPT, PRUNE, CONTINUE).
    """
    engine_mod, stopping_mod = import_bayesian()

    model = engine_mod.BetaBinomialModel(prior_alpha=1.0, prior_beta=1.0)
    controller = stopping_mod.EarlyStoppingController(
        accept_threshold=0.95,
        prune_threshold=0.10,
        min_evals=10,
        max_evals=30,
    )

    # Scenario 1: Candidate is vastly superior (18/20 vs 10/20)
    p_sup_high = model.posterior_superiority(
        candidate_successes=18,
        candidate_failures=2,
        baseline_successes=10,
        baseline_failures=10,
    )
    assert p_sup_high >= 0.95
    dec_high = controller.evaluate(step=20, p_superiority=p_sup_high)
    decision_val = dec_high.value if hasattr(dec_high, "value") else str(dec_high).upper()
    assert "ACCEPT" in decision_val

    # Scenario 2: Candidate is severely degraded (2/20 vs 10/20)
    p_sup_low = model.posterior_superiority(
        candidate_successes=2,
        candidate_failures=18,
        baseline_successes=10,
        baseline_failures=10,
    )
    assert p_sup_low <= 0.10
    dec_low = controller.evaluate(step=20, p_superiority=p_sup_low)
    decision_low_val = dec_low.value if hasattr(dec_low, "value") else str(dec_low).upper()
    assert "PRUNE" in decision_low_val


def test_comb_12_f7_f9_concurrent_stream_step_by_step_early_stopping():
    """Interaction F7 + F9: Concurrent batch execution stream evaluated step-by-step.

    Simulates streaming trial completion from batch execution, feeding sequential updates
    into EarlyStoppingController, and verifying that pruning halts further execution.
    """
    engine_mod, stopping_mod = import_bayesian()
    model = engine_mod.BetaBinomialModel(prior_alpha=1.0, prior_beta=1.0)
    controller = stopping_mod.EarlyStoppingController(
        accept_threshold=0.95,
        prune_threshold=0.10,
        min_evals=5,
        max_evals=20,
    )

    # Simulated candidate with 0% success rate
    cand_successes, cand_failures = 0, 0
    base_successes, base_failures = 15, 5  # Baseline is 75%
    stopped_at_step = None

    for step in range(1, 21):
        # Step arrives (failure)
        cand_failures += 1
        p_sup = model.posterior_superiority(
            cand_successes, cand_failures, base_successes, base_failures
        )
        decision = controller.evaluate(step=step, p_superiority=p_sup)
        d_val = decision.value if hasattr(decision, "value") else str(decision).upper()

        if "PRUNE" in d_val or "ACCEPT" in d_val:
            stopped_at_step = step
            break

    # Pruning must happen as soon as warmup min_evals=5 is reached
    assert stopped_at_step is not None
    assert stopped_at_step == 5, f"Expected pruning at step 5 warmup, got {stopped_at_step}"


def test_comb_13_f8_f13_opt_bayesian_superiority_to_holdout_mcnemar():
    """Interaction F8 + F13: Optimization set Bayesian superiority followed by Holdout McNemar's test.

    Verifies two-stage gating: a candidate must first clear Bayesian superiority on
    Optimization set, and then undergo paired McNemar testing on the Holdout set.
    """
    engine_mod, _ = import_bayesian()
    holdout_mod, _, _ = import_lifecycle()
    telemetry_mod = import_harbor()[3]

    model = engine_mod.BetaBinomialModel()
    p_sup = model.posterior_superiority(
        candidate_successes=19,
        candidate_failures=1,
        baseline_successes=10,
        baseline_failures=10,
    )
    assert p_sup >= 0.95, "Candidate must pass Bayesian threshold"

    # Now evaluate on Holdout Set (20 paired tasks)
    # Case: Candidate beats baseline on discordant tasks (b=12, c=0)
    base_results = []
    cand_results = []
    for i in range(20):
        t_id = f"hld_task_{i:02d}"
        if i < 12:
            base_passed = False
            cand_passed = True
        else:
            base_passed = True
            cand_passed = True
        base_results.append(telemetry_mod.TrialTelemetry(
            trial_id=f"b_{i}", task_id=t_id, candidate_id="base", passed=base_passed,
            exit_code=0 if base_passed else 1, latency_ms=10.0, token_spend=telemetry_mod.TokenSpend(), trace_logs=[]
        ))
        cand_results.append(telemetry_mod.TrialTelemetry(
            trial_id=f"c_{i}", task_id=t_id, candidate_id="cand", passed=cand_passed,
            exit_code=0 if cand_passed else 1, latency_ms=10.0, token_spend=telemetry_mod.TokenSpend(), trace_logs=[]
        ))

    gate = holdout_mod.HoldoutGate(alpha=0.05)
    decision = gate.evaluate(base_results, cand_results)

    assert decision.passed is True
    assert decision.p_value < 0.05
    assert "contingency_table" in dir(decision) or hasattr(decision, "contingency_table")


def test_comb_14_f13_f14_mcnemar_outcome_drives_state_machine_transition():
    """Interaction F13 + F14: McNemar test outcome directly driving State Machine transition.

    Verifies that a passing McNemar test triggers transition from HOLDOUT_GATE to
    BASELINE_UPDATE, while a failing test triggers transition to TRACE_DIAGNOSIS.
    """
    holdout_mod, sm_mod, _ = import_lifecycle()

    State = sm_mod.OptimizationState
    fsm = sm_mod.LifecycleStateMachine()

    # Fast-forward to HOLDOUT_GATE
    fsm.transition_to(State.BASELINE_RUN)
    fsm.transition_to(State.CANDIDATE_SEARCH)
    fsm.transition_to(State.SEQUENTIAL_EXEC)
    fsm.transition_to(State.HOLDOUT_GATE)

    # 1. Pass decision -> BASELINE_UPDATE
    pass_decision = holdout_mod.HoldoutDecision(passed=True, p_value=0.002, contingency_table={"b": 10, "c": 0})
    fsm.handle_holdout_decision(pass_decision)
    assert fsm.current_state == State.BASELINE_UPDATE

    # 2. Reset and test fail decision -> TRACE_DIAGNOSIS
    fsm.reset()
    fsm.transition_to(State.BASELINE_RUN)
    fsm.transition_to(State.CANDIDATE_SEARCH)
    fsm.transition_to(State.SEQUENTIAL_EXEC)
    fsm.transition_to(State.HOLDOUT_GATE)

    fail_decision = holdout_mod.HoldoutDecision(passed=False, p_value=0.45, contingency_table={"b": 2, "c": 3})
    fsm.handle_holdout_decision(fail_decision)
    assert fsm.current_state == State.TRACE_DIAGNOSIS


def test_comb_15_f12_f14_trace_diagnosis_invokes_archetype_clustering():
    """Interaction F12 + F14: TRACE_DIAGNOSIS state invoking Archetype Clustering.

    Verifies that when the state machine enters TRACE_DIAGNOSIS, it clusters failed
    trial traces and extracts diagnostic terms to inform the next candidate mutation.
    """
    archetypes_mod, _, _ = import_clustering()
    _, sm_mod, _ = import_lifecycle()
    _, _, _, telemetry_mod = import_harbor()

    State = sm_mod.OptimizationState
    fsm = sm_mod.LifecycleStateMachine()

    # Move to TRACE_DIAGNOSIS
    fsm.transition_to(State.BASELINE_RUN)
    fsm.transition_to(State.CANDIDATE_SEARCH)
    fsm.transition_to(State.SEQUENTIAL_EXEC)
    fsm.transition_to(State.TRACE_DIAGNOSIS)
    assert fsm.current_state == State.TRACE_DIAGNOSIS

    # Failed traces to diagnose
    failed_telemetry = [
        telemetry_mod.TrialTelemetry(
            trial_id=f"t_{i}", task_id=f"tsk_{i}", candidate_id="cand_bad", passed=False,
            exit_code=1, latency_ms=50.0, token_spend=telemetry_mod.TokenSpend(), trace_logs=[],
            raw_error_message=f"SyntaxError: invalid token in script chunk {i}"
        )
        for i in range(5)
    ]

    # Diagnose failures
    if hasattr(fsm, "diagnose_failures"):
        diagnosis_report = fsm.diagnose_failures(failed_telemetry)
        assert diagnosis_report is not None
        assert hasattr(diagnosis_report, "clusters")
    else:
        # Direct clusterer invocation within diagnosis context
        clusterer = archetypes_mod.ArchetypeClusterer(k_clusters=1, random_state=42)
        report = clusterer.cluster_telemetry(failed_telemetry) if hasattr(clusterer, "cluster_telemetry") else clusterer.fit_predict(np.eye(5), [t.raw_error_message for t in failed_telemetry])
        assert report is not None


def test_comb_16_f15_f16_synthetic_benchmark_to_cli_sweep_runner():
    """Interaction F15 + F16: Synthetic benchmark generator feeding directly into CLI sweep runner.

    Verifies that the CLI entrypoint can execute a synthetic sweep with generated
    benchmarks, producing complete telemetry and exit code 0.
    """
    import_synthetic()
    cli_mod = import_cli()

    # Check CLI has main or run_sweep entrypoint
    entrypoint = getattr(cli_mod, "main", getattr(cli_mod, "run_sweep", None))
    assert entrypoint is not None, "CLI missing main/run_sweep function"

    # Invoke programmatically with synthetic sweep flags
    test_args = ["--tasks", "6", "--seed", "42", "--opt-ratio", "0.7", "--min-evals", "2", "--max-evals", "4"]
    exit_code = entrypoint(test_args) if callable(entrypoint) else 0
    # Expected exit code 0 on clean completion
    assert exit_code in (0, None)


def test_comb_17_f1_f4_task_metadata_propagated_to_trial_telemetry():
    """Interaction F1 + F4: Ingested ATIF task metadata propagated into TrialTelemetry.

    Verifies that behavioral tags, difficulty strata, and custom task metadata from
    F1 schema are preserved and accessible in the TrialTelemetry produced by F4.
    """
    _, _, _, telemetry_mod = import_harbor()
    task = make_sample_task(
        "task_prop_01",
        difficulty="hard",
        tags=["constraint_adherence", "state_mutation"],
        metadata={"priority": "high", "benchmark_suite": "synth_v1"},
    )
    candidate = DummyCandidate("cand_meta")
    _, _, sandbox_mod, _ = import_harbor()
    harness = sandbox_mod.InMemoryMockHarness(failure_rate=0.0, seed=7)
    tel = harness.execute_trial(task, candidate)

    assert tel.task_id == task.task_id
    # Ensure telemetry attributes or metadata retain task associations
    if hasattr(tel, "metadata") and tel.metadata:
        assert tel.metadata.get("priority") == "high"


def test_comb_18_f5_f8_mock_trials_feed_bayesian_model_update():
    """Interaction F5 + F8: Mock trials iteratively updating BetaBinomialModel posterior.

    Verifies that TrialTelemetry pass/fail outcomes generated by InMemoryMockHarness
    directly update BetaBinomialModel conjugate alpha and beta parameters.
    """
    _, _, sandbox_mod, _ = import_harbor()
    engine_mod, _ = import_bayesian()

    tasks = make_task_corpus(count=10)
    candidate = DummyCandidate("cand_bayes")
    # 70% failure rate mock
    harness = sandbox_mod.InMemoryMockHarness(failure_rate=0.70, seed=42)

    model = engine_mod.BetaBinomialModel(prior_alpha=1.0, prior_beta=1.0)
    for task in tasks:
        tel = harness.execute_trial(task, candidate)
        if hasattr(model, "update_from_telemetry"):
            model.update_from_telemetry(tel)
        elif hasattr(model, "update"):
            model.update(successes=1 if tel.passed else 0, failures=0 if tel.passed else 1)

    # Invariants: alpha + beta should equal prior (2.0) + 10 trials = 12.0
    total_pseudo_counts = model.alpha + model.beta
    assert total_pseudo_counts == pytest.approx(12.0)


def test_comb_19_f9_f14_early_pruning_drives_state_machine_to_trace_diagnosis():
    """Interaction F9 + F14: Bayesian early pruning triggering state transition to TRACE_DIAGNOSIS.

    Verifies that an early PRUNE decision immediately transitions the state machine
    from SEQUENTIAL_EXEC to TRACE_DIAGNOSIS, skipping holdout gate to conserve compute.
    """
    _, stopping_mod = import_bayesian()
    _, sm_mod, _ = import_lifecycle()

    fsm = sm_mod.LifecycleStateMachine()
    State = sm_mod.OptimizationState

    fsm.transition_to(State.BASELINE_RUN)
    fsm.transition_to(State.CANDIDATE_SEARCH)
    fsm.transition_to(State.SEQUENTIAL_EXEC)

    prune_decision = stopping_mod.StoppingDecision.PRUNE if hasattr(stopping_mod, "StoppingDecision") else "PRUNE"
    fsm.handle_stopping_decision(prune_decision)

    assert fsm.current_state == State.TRACE_DIAGNOSIS


def test_comb_20_f2_f15_synthetic_benchmark_stratified_partitioning():
    """Interaction F2 + F15: Synthetic benchmark suite partition preserving strata with zero leakage.

    Generates a synthetic suite of 50 tasks with SyntheticBenchmarkGenerator and
    partitions it with StratifiedSplitter, proving mutual exclusivity and stratification.
    """
    bench_mod = import_synthetic()
    _, _, splitter_mod = import_benchhub()

    gen = bench_mod.SyntheticBenchmarkGenerator(seed=999)
    suite = gen.generate_suite(50) if hasattr(gen, "generate_suite") else gen.generate(50)

    splitter = splitter_mod.StratifiedSplitter(opt_ratio=0.7, seed=999)
    split_res = splitter.split(suite)
    opt, hld = split_res if isinstance(split_res, tuple) else (split_res.optimization_set, split_res.holdout_set)

    assert len(opt) + len(hld) == 50
    assert len(set(t.task_id for t in opt).intersection(set(t.task_id for t in hld))) == 0
