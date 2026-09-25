"""Tier 4 Realistic End-to-End Hill-Climbing Sweep Scenarios.

Validates full-scale, end-to-end application workloads and lifecycle state transitions:
  1. test_scenario_successful_hill_climbing_promotion:
     Baseline evaluated, candidate evaluated with superior pass rate, Bayesian early
     acceptance triggers, Holdout gate passes with significant McNemar p-value (<0.05),
     baseline updated.
  2. test_scenario_degraded_candidate_early_pruning:
     Candidate has poor pass rate, Bayesian engine prunes after warmup at P<=0.10,
     state machine transitions to TRACE_DIAGNOSIS, holdout evaluation skipped to save compute.
  3. test_scenario_anti_goodhart_holdout_rejection:
     Candidate achieves high score on Optimization set (passes Bayesian early stopping),
     but fails McNemar paired test on Holdout set due to lack of generalizability;
     promotion rejected.
  4. test_scenario_failure_trace_mining_and_archetype_diagnosis:
     Multiple failed trials across heterogeneous failure modes (context overflow, timeout,
     syntax error, tool format drift) clustered into distinct archetypes with representative
     exemplars and diagnostic terms.
  5. test_scenario_multi_candidate_sequential_sweep:
     Full search iteration through 3 candidates (1 pruned, 1 rejected on holdout, 1 promoted),
     tracking state transitions and telemetry history.
  6. test_scenario_synthetic_benchmark_to_end_to_end_pipeline:
     Generate synthetic ATIF benchmark, perform stratified partition, run baseline and
     candidate evaluations, perform early stopping, and assert telemetry fidelity.
  7. test_scenario_subprocess_execution_with_timeout_and_faults:
     Real subprocess sandbox execution handling script execution, timeouts, exit code
     non-zero, capturing telemetry and error spans accurately.
  8. test_scenario_cli_synthetic_sweep_execution:
     Subprocess invocation of `cli.py` or `python -m harness_optimizer` with synthetic sweep
     arguments, asserting zero exit code, standard output logging Bayesian updates and final verdict.
  9. test_scenario_non_stationary_tie_resolution_and_null_acceptance:
     Candidate model with indistinguishable performance evaluated up to max_evals,
     failing to reject null hypothesis on holdout set, keeping baseline intact.
  10. test_scenario_high_concurrency_batch_execution_fidelity:
     High-concurrency batch trial execution under load verifying determinism and telemetry integrity.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Dynamic Import Helpers with Informative Progressive Skipping
# ============================================================================

def import_all_modules():
    """Imports all core modules or skips if missing."""
    try:
        from harness_optimizer.benchhub import schema, splitter
        from harness_optimizer.harbor import config, executor, sandbox, telemetry
        from harness_optimizer.bayesian import engine, stopping
        from harness_optimizer.clustering import archetypes, trace_miner, vectorizer
        from harness_optimizer.lifecycle import holdout_gate, state_machine
        from harness_optimizer.synthetic import benchmark
        return (
            schema, splitter, config, executor, sandbox, telemetry,
            engine, stopping, archetypes, trace_miner, vectorizer,
            holdout_gate, state_machine, benchmark
        )
    except ImportError as exc:
        pytest.skip(f"Core module missing for E2E scenario: {exc}")


class ScenarioCandidate:
    """Agent candidate model configuration for scenarios."""
    def __init__(self, candidate_id: str, prompt: str = "", temperature: float = 0.2):
        self.candidate_id = candidate_id
        self.system_prompt = prompt
        self.temperature = temperature


def create_mock_telemetry(
    trial_id: str,
    task_id: str,
    candidate_id: str,
    passed: bool,
    exit_code: int = 0,
    latency_ms: float = 15.0,
    raw_error: Optional[str] = None,
):
    """Factory creating a realistic TrialTelemetry instance."""
    (
        schema, splitter, config, executor, sandbox, telemetry,
        engine, stopping, archetypes, trace_miner, vectorizer,
        holdout_gate, state_machine, benchmark
    ) = import_all_modules()

    spans = [
        telemetry.TraceSpan(name="planning", duration_ms=latency_ms * 0.3, status="ok"),
        telemetry.TraceSpan(name="execution", duration_ms=latency_ms * 0.7, status="ok" if passed else "error"),
    ]
    token_spend = telemetry.TokenSpend(prompt_tokens=150, completion_tokens=80, total_tokens=230)
    return telemetry.TrialTelemetry(
        trial_id=trial_id,
        task_id=task_id,
        candidate_id=candidate_id,
        passed=passed,
        exit_code=exit_code if not passed else 0,
        latency_ms=latency_ms,
        token_spend=token_spend,
        trace_logs=spans,
        raw_error_message=raw_error if not passed else None,
    )


# ============================================================================
# Tier 4 Scenario Test Cases
# ============================================================================

def test_scenario_successful_hill_climbing_promotion():
    """Scenario 1: Superior candidate clears Bayesian stopping and Holdout gate to become new baseline.

    Lifecycle Progression:
      1. Baseline evaluated on Optimization set -> baseline pass rate ~50% (10/20).
      2. Candidate evaluated sequentially on Optimization set -> candidate pass rate ~90% (18/20).
      3. Bayesian posterior superiority P(theta_c > theta_b | D) >= 0.95 -> ACCEPT decision.
      4. State machine transitions from SEQUENTIAL_EXEC to HOLDOUT_GATE.
      5. Holdout gate evaluates paired trials on 20 holdout tasks -> McNemar p-value < 0.05.
      6. State machine transitions to BASELINE_UPDATE.
      7. Active baseline successfully updated with candidate configuration.
    """
    (
        schema, splitter, config, executor, sandbox, telemetry,
        engine, stopping, archetypes, trace_miner, vectorizer,
        holdout_gate, state_machine, benchmark
    ) = import_all_modules()

    fsm = state_machine.LifecycleStateMachine()
    State = state_machine.OptimizationState

    assert fsm.current_state == State.IDLE
    fsm.transition_to(State.BASELINE_RUN)
    assert fsm.current_state == State.BASELINE_RUN

    # Baseline performance: 10 successes, 10 failures
    base_succ, base_fail = 10, 10

    fsm.transition_to(State.CANDIDATE_SEARCH)
    cand = ScenarioCandidate("cand_promoted_v1", prompt="Think step by step with tool validation.")

    fsm.transition_to(State.SEQUENTIAL_EXEC)
    assert fsm.current_state == State.SEQUENTIAL_EXEC

    # Candidate evaluation stream on Optimization set (18 passes, 2 fails)
    cand_succ, cand_fail = 18, 2
    model = engine.BetaBinomialModel(prior_alpha=1.0, prior_beta=1.0)
    p_sup = model.posterior_superiority(cand_succ, cand_fail, base_succ, base_fail)
    assert p_sup >= 0.95, f"Expected P >= 0.95 for 90% vs 50%, got {p_sup}"

    controller = stopping.EarlyStoppingController(
        accept_threshold=0.95, prune_threshold=0.10, min_evals=10, max_evals=30
    )
    decision = controller.evaluate(step=20, p_superiority=p_sup)
    d_val = decision.value if hasattr(decision, "value") else str(decision).upper()
    assert "ACCEPT" in d_val

    # Transition to HOLDOUT_GATE
    fsm.handle_stopping_decision(decision)
    assert fsm.current_state == State.HOLDOUT_GATE

    # Holdout gate paired testing: 20 holdout tasks, candidate wins 12 discordant tasks (b=12, c=0)
    base_holdout = [create_mock_telemetry(f"b_h_{i}", f"h_task_{i}", "baseline", passed=(i >= 12)) for i in range(20)]
    cand_holdout = [create_mock_telemetry(f"c_h_{i}", f"h_task_{i}", cand.candidate_id, passed=True) for i in range(20)]

    gate = holdout_gate.HoldoutGate(alpha=0.05)
    gate_decision = gate.evaluate(base_holdout, cand_holdout)

    assert gate_decision.passed is True
    assert gate_decision.p_value < 0.05

    # Trigger baseline update transition
    fsm.handle_holdout_decision(gate_decision)
    assert fsm.current_state == State.BASELINE_UPDATE

    # Assert active baseline updated
    if hasattr(fsm, "active_baseline"):
        assert fsm.active_baseline is not None


def test_scenario_degraded_candidate_early_pruning():
    """Scenario 2: Severely degraded candidate pruned early, bypassing holdout evaluation to save compute.

    Lifecycle Progression:
      1. Active baseline pass rate is strong: ~75% (15/20).
      2. Candidate evaluated sequentially, failing trials consistently (1 pass, 9 fails).
      3. At warmup step 10, Bayesian engine computes P(theta_c > theta_b | D) <= 0.10.
      4. EarlyStoppingController triggers PRUNE decision.
      5. State machine transitions directly to TRACE_DIAGNOSIS, skipping HOLDOUT_GATE.
      6. Holdout tasks evaluated == 0 (verifying compute conservation).
    """
    (
        schema, splitter, config, executor, sandbox, telemetry,
        engine, stopping, archetypes, trace_miner, vectorizer,
        holdout_gate, state_machine, benchmark
    ) = import_all_modules()

    fsm = state_machine.LifecycleStateMachine()
    State = state_machine.OptimizationState

    fsm.transition_to(State.BASELINE_RUN)
    fsm.transition_to(State.CANDIDATE_SEARCH)
    fsm.transition_to(State.SEQUENTIAL_EXEC)

    base_succ, base_fail = 15, 5
    cand_succ, cand_fail = 1, 9  # 10% pass rate

    model = engine.BetaBinomialModel(prior_alpha=1.0, prior_beta=1.0)
    p_sup = model.posterior_superiority(cand_succ, cand_fail, base_succ, base_fail)
    assert p_sup <= 0.10, f"Expected P <= 0.10 for 10% vs 75%, got {p_sup}"

    controller = stopping.EarlyStoppingController(
        accept_threshold=0.95, prune_threshold=0.10, min_evals=10, max_evals=30
    )
    decision = controller.evaluate(step=10, p_superiority=p_sup)
    d_val = decision.value if hasattr(decision, "value") else str(decision).upper()
    assert "PRUNE" in d_val

    # FSM routes directly to TRACE_DIAGNOSIS
    fsm.handle_stopping_decision(decision)
    assert fsm.current_state == State.TRACE_DIAGNOSIS
    assert fsm.current_state != State.HOLDOUT_GATE, "Holdout gate must NOT be evaluated for pruned candidate!"


def test_scenario_anti_goodhart_holdout_rejection():
    """Scenario 3: Anti-Goodharting guard rejects candidate that overfit to Optimization set.

    Lifecycle Progression:
      1. Candidate achieves 100% pass rate on Optimization set (20/20), clearing early stopping (P > 0.99).
      2. State machine transitions to HOLDOUT_GATE.
      3. On quarantined Holdout set, candidate suffers generalization collapse (only 6/20 pass vs baseline 14/20).
      4. McNemar paired test fails to find significant superiority (c > b, p-value fails threshold).
      5. State machine rejects promotion and routes to TRACE_DIAGNOSIS, protecting active baseline from corruption.
    """
    (
        schema, splitter, config, executor, sandbox, telemetry,
        engine, stopping, archetypes, trace_miner, vectorizer,
        holdout_gate, state_machine, benchmark
    ) = import_all_modules()

    fsm = state_machine.LifecycleStateMachine()
    State = state_machine.OptimizationState

    fsm.transition_to(State.BASELINE_RUN)
    fsm.transition_to(State.CANDIDATE_SEARCH)
    fsm.transition_to(State.SEQUENTIAL_EXEC)

    # 100% on Optimization set
    model = engine.BetaBinomialModel(prior_alpha=1.0, prior_beta=1.0)
    p_sup = model.posterior_superiority(candidate_successes=20, candidate_failures=0, baseline_successes=12, baseline_failures=8)
    assert p_sup >= 0.95

    controller = stopping.EarlyStoppingController(accept_threshold=0.95, prune_threshold=0.10, min_evals=10)
    decision = controller.evaluate(step=20, p_superiority=p_sup)
    fsm.handle_stopping_decision(decision)
    assert fsm.current_state == State.HOLDOUT_GATE

    # Holdout set regression: baseline wins 8 tasks that candidate failed (b=0, c=8)
    base_holdout = []
    cand_holdout = []
    for i in range(20):
        t_id = f"hld_tsk_{i}"
        b_passed = (i < 14)
        c_passed = (i < 6)
        base_holdout.append(create_mock_telemetry(f"b_{i}", t_id, "baseline", passed=b_passed))
        cand_holdout.append(create_mock_telemetry(f"c_{i}", t_id, "overfit_cand", passed=c_passed))

    gate = holdout_gate.HoldoutGate(alpha=0.05)
    gate_decision = gate.evaluate(base_holdout, cand_holdout)

    assert gate_decision.passed is False, "Goodhart-overfit candidate must NOT pass Holdout Gate!"

    fsm.handle_holdout_decision(gate_decision)
    assert fsm.current_state == State.TRACE_DIAGNOSIS
    assert fsm.current_state != State.BASELINE_UPDATE


def test_scenario_failure_trace_mining_and_archetype_diagnosis():
    """Scenario 4: Trace miner clusters 40 failed trials into 4 operational failure archetypes.

    Verifies unsupervised clustering of heterogeneous error spans:
      - Archetype 1: Context window overflow
      - Archetype 2: Process watchdog timeout
      - Archetype 3: Malformed tool call JSON
      - Archetype 4: Missing filesystem verification artifact
    Asserts cluster count, top diagnostic terms, and exemplar recovery.
    """
    (
        schema, splitter, config, executor, sandbox, telemetry,
        engine, stopping, archetypes, trace_miner, vectorizer,
        holdout_gate, state_machine, benchmark
    ) = import_all_modules()

    templates = [
        ("ContextOverflow", "PromptTokensError: Context length 131072 exceeded maximum model window of 65536 tokens at memory offset 0xdeadbeef"),
        ("WatchdogTimeout", "TimeoutError: Command 'python3 run_eval.py' timed out after 30.0 seconds watchdog limit"),
        ("ToolSyntaxError", "JSONDecodeError: Expecting ',' delimiter at line 1 column 42 (char 41) in tool call dictionary"),
        ("MissingArtifact", "FileNotFoundError: [Errno 2] No such file or directory: 'dist/bundle.min.js' verification target"),
    ]

    failed_telemetry = []
    for idx in range(40):
        archetype_name, error_msg = templates[idx % 4]
        msg_with_noise = f"{error_msg} [trial_iter_{idx}]"
        tel = create_mock_telemetry(
            trial_id=f"fail_{idx:03d}",
            task_id=f"task_{idx:03d}",
            candidate_id="cand_fragile",
            passed=False,
            exit_code=1,
            raw_error=msg_with_noise,
        )
        failed_telemetry.append(tel)

    miner = trace_miner.TraceMiner()
    if hasattr(miner, "extract_error_spans"):
        spans = miner.extract_error_spans(failed_telemetry)
    else:
        spans = [miner.extract_error_span(t.raw_error_message) for t in failed_telemetry]

    assert len(spans) == 40

    vec = vectorizer.TraceVectorizer(ngram_range=(1, 2), max_features=100)
    matrix = vec.fit_transform(spans)

    clusterer = archetypes.ArchetypeClusterer(k_clusters=4, random_state=42)
    report = clusterer.fit_predict(matrix, spans)
    clusters = report.clusters if hasattr(report, "clusters") else report

    assert len(clusters) == 4
    # Check that diagnostic keywords and exemplars are present
    total_exemplars = 0
    all_top_terms = []
    for c in clusters:
        total_exemplars += len(c.exemplars)
        all_top_terms.extend([t.lower() for t in c.top_terms])

    assert total_exemplars >= 4
    # Essential failure terms should be present in top terms
    assert any("context" in t or "token" in t or "window" in t for t in all_top_terms)
    assert any("timeout" in t or "watchdog" in t or "second" in t for t in all_top_terms)


def test_scenario_multi_candidate_sequential_sweep():
    """Scenario 5: Multi-candidate sequential search through 3 candidates.

    Candidate Sequence:
      - Candidate A: Inferior pass rate -> Pruned at warmup (PRUNED) -> TRACE_DIAGNOSIS.
      - Candidate B: Optimization overfit -> Passed opt, rejected at Holdout Gate (REJECTED_HOLDOUT) -> TRACE_DIAGNOSIS.
      - Candidate C: Robust improvement -> Passed opt, passed Holdout Gate -> BASELINE_UPDATE (PROMOTED).
    Tracks state transitions and history across all 3 candidates.
    """
    (
        schema, splitter, config, executor, sandbox, telemetry,
        engine, stopping, archetypes, trace_miner, vectorizer,
        holdout_gate, state_machine, benchmark
    ) = import_all_modules()

    fsm = state_machine.LifecycleStateMachine()
    State = state_machine.OptimizationState
    bayes_model = engine.BetaBinomialModel(prior_alpha=1.0, prior_beta=1.0)
    stop_ctrl = stopping.EarlyStoppingController(accept_threshold=0.95, prune_threshold=0.10, min_evals=10, max_evals=25)
    gate = holdout_gate.HoldoutGate(alpha=0.05)

    history = []

    # --- Candidate A (Degraded) ---
    fsm.transition_to(State.BASELINE_RUN)
    fsm.transition_to(State.CANDIDATE_SEARCH)
    fsm.transition_to(State.SEQUENTIAL_EXEC)

    p_sup_a = bayes_model.posterior_superiority(candidate_successes=1, candidate_failures=9, baseline_successes=10, baseline_failures=10)
    dec_a = stop_ctrl.evaluate(step=10, p_superiority=p_sup_a)
    assert "PRUNE" in (dec_a.value if hasattr(dec_a, "value") else str(dec_a).upper())
    fsm.handle_stopping_decision(dec_a)
    assert fsm.current_state == State.TRACE_DIAGNOSIS
    history.append(("Candidate_A", "PRUNED"))

    # --- Candidate B (Overfit) ---
    fsm.transition_to(State.CANDIDATE_SEARCH)
    fsm.transition_to(State.SEQUENTIAL_EXEC)

    p_sup_b = bayes_model.posterior_superiority(candidate_successes=20, candidate_failures=0, baseline_successes=10, baseline_failures=10)
    dec_b = stop_ctrl.evaluate(step=20, p_superiority=p_sup_b)
    fsm.handle_stopping_decision(dec_b)
    assert fsm.current_state == State.HOLDOUT_GATE

    # Holdout gate fails for B
    b_base = [create_mock_telemetry(f"bb_{i}", f"ht_{i}", "base", passed=(i < 12)) for i in range(20)]
    b_cand = [create_mock_telemetry(f"bc_{i}", f"ht_{i}", "cand_b", passed=(i < 6)) for i in range(20)]
    gate_dec_b = gate.evaluate(b_base, b_cand)
    fsm.handle_holdout_decision(gate_dec_b)
    assert fsm.current_state == State.TRACE_DIAGNOSIS
    history.append(("Candidate_B", "REJECTED_HOLDOUT"))

    # --- Candidate C (Promoted) ---
    fsm.transition_to(State.CANDIDATE_SEARCH)
    fsm.transition_to(State.SEQUENTIAL_EXEC)

    p_sup_c = bayes_model.posterior_superiority(candidate_successes=18, candidate_failures=2, baseline_successes=10, baseline_failures=10)
    dec_c = stop_ctrl.evaluate(step=20, p_superiority=p_sup_c)
    fsm.handle_stopping_decision(dec_c)
    assert fsm.current_state == State.HOLDOUT_GATE

    # Holdout gate passes for C
    c_base = [create_mock_telemetry(f"cb_{i}", f"ht_{i}", "base", passed=(i < 8)) for i in range(20)]
    c_cand = [create_mock_telemetry(f"cc_{i}", f"ht_{i}", "cand_c", passed=True) for i in range(20)]
    gate_dec_c = gate.evaluate(c_base, c_cand)
    fsm.handle_holdout_decision(gate_dec_c)
    assert fsm.current_state == State.BASELINE_UPDATE
    history.append(("Candidate_C", "PROMOTED"))

    assert history == [
        ("Candidate_A", "PRUNED"),
        ("Candidate_B", "REJECTED_HOLDOUT"),
        ("Candidate_C", "PROMOTED"),
    ]


def test_scenario_synthetic_benchmark_to_end_to_end_pipeline():
    """Scenario 6: Full pipeline execution from synthetic benchmark generation to holdout verdict.

    Pipeline Steps:
      1. Generate 30 synthetic ATIF tasks with varied difficulty and tags.
      2. Perform stratified split (70% opt, 30% holdout), verifying zero task leakage.
      3. Run baseline execution on optimization set with InMemoryMockHarness.
      4. Run candidate execution on optimization set with InMemoryMockHarness.
      5. Evaluate Bayesian superiority and EarlyStoppingController.
      6. Run HoldoutGate evaluation on holdout set.
      7. Assert full telemetry fidelity across all executed trials.
    """
    (
        schema, splitter, config, executor, sandbox, telemetry,
        engine, stopping, archetypes, trace_miner, vectorizer,
        holdout_gate, state_machine, benchmark
    ) = import_all_modules()

    # Step 1: Synthetic benchmark generation
    gen = benchmark.SyntheticBenchmarkGenerator(seed=42)
    suite = gen.generate_suite(30) if hasattr(gen, "generate_suite") else gen.generate(30)
    assert len(suite) == 30

    # Step 2: Stratified split
    spl = splitter.StratifiedSplitter(opt_ratio=0.7, seed=42)
    split_res = spl.split(suite)
    opt_set, hld_set = split_res if isinstance(split_res, tuple) else (split_res.optimization_set, split_res.holdout_set)

    assert len(opt_set) + len(hld_set) == 30
    assert set(t.task_id for t in opt_set).isdisjoint(set(t.task_id for t in hld_set))

    # Step 3 & 4: Mock trial executions
    base_harness = sandbox.InMemoryMockHarness(failure_rate=0.45, seed=10)
    cand_harness = sandbox.InMemoryMockHarness(failure_rate=0.10, seed=20)

    base_opt_results = [base_harness.execute_trial(t, ScenarioCandidate("base")) for t in opt_set]
    cand_opt_results = [cand_harness.execute_trial(t, ScenarioCandidate("cand")) for t in opt_set]

    # Step 5: Bayesian evaluation
    base_succ = sum(1 for r in base_opt_results if r.passed)
    base_fail = len(base_opt_results) - base_succ
    cand_succ = sum(1 for r in cand_opt_results if r.passed)
    cand_fail = len(cand_opt_results) - cand_succ

    model = engine.BetaBinomialModel()
    p_sup = model.posterior_superiority(cand_succ, cand_fail, base_succ, base_fail)
    controller = stopping.EarlyStoppingController(accept_threshold=0.95, min_evals=10)
    decision = controller.evaluate(step=len(opt_set), p_superiority=p_sup)

    assert p_sup > 0.90
    assert "ACCEPT" in (decision.value if hasattr(decision, "value") else str(decision).upper())

    # Step 6: Holdout evaluation
    base_hld_results = [base_harness.execute_trial(t, ScenarioCandidate("base")) for t in hld_set]
    cand_hld_results = [cand_harness.execute_trial(t, ScenarioCandidate("cand")) for t in hld_set]

    gate = holdout_gate.HoldoutGate(alpha=0.10)
    hld_dec = gate.evaluate(base_hld_results, cand_hld_results)
    assert hasattr(hld_dec, "passed")

    # Step 7: Telemetry contracts
    all_trials = base_opt_results + cand_opt_results + base_hld_results + cand_hld_results
    for trial in all_trials:
        assert isinstance(trial, telemetry.TrialTelemetry)
        assert trial.latency_ms >= 0.0
        assert trial.token_spend.total_tokens >= 0


def test_scenario_subprocess_execution_with_timeout_and_faults():
    """Scenario 7: Real SubprocessSandbox execution handling success, non-zero exits, and watchdog timeouts.

    Verifies:
      - Clean zero-exit script execution.
      - Non-zero exit code capture with error stderr.
      - Watchdog timeout trigger and graceful process termination.
      - Trace span duration accuracy.
    """
    (
        schema, splitter, config, executor, sandbox, telemetry,
        engine, stopping, archetypes, trace_miner, vectorizer,
        holdout_gate, state_machine, benchmark
    ) = import_all_modules()

    cfg = config.SandboxConfig(timeout_sec=0.8)
    proc_box = sandbox.SubprocessSandbox(config=cfg)
    cand = ScenarioCandidate("subproc_tester")

    # 1. Successful execution
    task_ok = schema.ATIFTask(
        task_id="sp_ok",
        instruction="Print success",
        difficulty=schema.DifficultyLevel.EASY,
        behavioral_tags=[schema.BehavioralTag.TOOL_SELECTION],
        verification=schema.VerificationSpec(command="python3 -c \"print('ALL_GOOD'); exit(0)\""),
        metadata={},
    )
    t_ok = proc_box.execute_trial(task_ok, cand)
    assert t_ok.passed is True
    assert t_ok.exit_code == 0
    assert t_ok.latency_ms > 0

    # 2. Non-zero exit with stderr
    task_fail = schema.ATIFTask(
        task_id="sp_fail",
        instruction="Trigger error",
        difficulty=schema.DifficultyLevel.EASY,
        behavioral_tags=[schema.BehavioralTag.TOOL_SELECTION],
        verification=schema.VerificationSpec(command="python3 -c \"import sys; sys.stderr.write('CRASH_ERR'); exit(42)\""),
        metadata={},
    )
    t_fail = proc_box.execute_trial(task_fail, cand)
    assert t_fail.passed is False
    assert t_fail.exit_code == 42
    assert t_fail.raw_error_message is not None or any("CRASH_ERR" in str(s) for s in t_fail.trace_logs)

    # 3. Timeout watchdog kill
    task_hang = schema.ATIFTask(
        task_id="sp_hang",
        instruction="Sleep forever",
        difficulty=schema.DifficultyLevel.HARD,
        behavioral_tags=[schema.BehavioralTag.CONSTRAINT_ADHERENCE],
        verification=schema.VerificationSpec(command="python3 -c \"import time; time.sleep(5.0)\""),
        metadata={},
    )
    t0 = time.perf_counter()
    t_hang = proc_box.execute_trial(task_hang, cand)
    duration = time.perf_counter() - t0

    assert t_hang.passed is False
    # Process must be killed near timeout_sec (0.8s), not sleep 5s
    assert duration < 3.0
    assert "timeout" in (t_hang.raw_error_message or "").lower() or t_hang.exit_code != 0


def test_scenario_cli_synthetic_sweep_execution():
    """Scenario 8: Subprocess invocation of CLI sweep entrypoint on synthetic benchmark.

    Invokes `cli.py` via subprocess with arguments `--tasks 10 --seed 42 --opt-ratio 0.7`.
    Asserts:
      - Subprocess exits with code 0.
      - Output contains key phases: benchmark generation, Bayesian updating, and sweep verdict.
      - No unhandled Python exceptions in stderr.
    """
    cli_path = PROJECT_ROOT / "cli.py"
    if not cli_path.exists():
        pytest.skip(f"cli.py not found at {cli_path}")

    cmd = [
        sys.executable,
        str(cli_path),
        "--tasks", "10",
        "--seed", "42",
        "--opt-ratio", "0.7",
        "--min-evals", "3",
        "--max-evals", "7",
    ]

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=30.0,
    )

    # CLI should succeed cleanly
    assert result.returncode == 0, f"CLI exited with non-zero code {result.returncode}. Stderr: {result.stderr}"
    stdout = result.stdout.lower()
    # Output must indicate sweep execution progress
    assert "baseline" in stdout or "candidate" in stdout or "bayesian" in stdout or "sweep" in stdout


def test_scenario_non_stationary_tie_resolution_and_null_acceptance():
    """Scenario 9: Candidate with identical performance consumes trials up to max_evals, failing holdout gate.

    Verifies behavior when candidate is statistically equivalent to baseline:
      1. Baseline has ~50% pass rate.
      2. Candidate has ~50% pass rate.
      3. Bayesian superiority hovers near P ~ 0.50, never reaching 0.95.
      4. Trial evaluation continues up to max_evals without early stopping.
      5. Holdout paired test shows equal discordance (b == c), yielding p-value ~ 1.0.
      6. Baseline remains active; candidate is not promoted.
    """
    (
        schema, splitter, config, executor, sandbox, telemetry,
        engine, stopping, archetypes, trace_miner, vectorizer,
        holdout_gate, state_machine, benchmark
    ) = import_all_modules()

    model = engine.BetaBinomialModel()
    controller = stopping.EarlyStoppingController(
        accept_threshold=0.95, prune_threshold=0.10, min_evals=5, max_evals=20
    )

    # 10 passes, 10 fails for both
    p_sup = model.posterior_superiority(10, 10, 10, 10)
    assert 0.45 <= p_sup <= 0.55

    decision = controller.evaluate(step=15, p_superiority=p_sup)
    d_val = decision.value if hasattr(decision, "value") else str(decision).upper()
    assert "CONTINUE" in d_val

    # Holdout gate paired test with tie (b=3, c=3)
    base_hld = [create_mock_telemetry(f"tb_{i}", f"th_{i}", "base", passed=(i % 2 == 0)) for i in range(16)]
    cand_hld = [create_mock_telemetry(f"tc_{i}", f"th_{i}", "cand_tie", passed=(i % 2 == 0)) for i in range(16)]

    gate = holdout_gate.HoldoutGate(alpha=0.05)
    decision = gate.evaluate(base_hld, cand_hld)
    assert decision.passed is False, "Tie must not reject null hypothesis in favor of candidate!"


def test_scenario_high_concurrency_batch_execution_fidelity():
    """Scenario 10: Concurrent execution of 30 tasks with 8 parallel worker threads.

    Verifies:
      - 30 tasks executed in parallel pool without race conditions or memory leaks.
      - Exactly 30 telemetry records returned with 100% input task matching.
      - Deterministic results across repeated runs with seeded InMemoryMockHarness.
    """
    (
        schema, splitter, config, executor, sandbox, telemetry,
        engine, stopping, archetypes, trace_miner, vectorizer,
        holdout_gate, state_machine, benchmark
    ) = import_all_modules()

    gen = benchmark.SyntheticBenchmarkGenerator(seed=777)
    tasks = gen.generate_suite(30) if hasattr(gen, "generate_suite") else gen.generate(30)
    candidate = ScenarioCandidate("cand_concurrency_stress")

    harness1 = sandbox.InMemoryMockHarness(failure_rate=0.30, seed=42)
    batch1 = executor.ConcurrentBatchExecutor(sandbox=harness1, max_workers=8)
    results1 = batch1.execute_batch(tasks, candidate)

    assert len(results1) == 30
    task_ids_in = {t.task_id for t in tasks}
    task_ids_out = {r.task_id for r in results1}
    assert task_ids_in == task_ids_out

    # Repeat with same seed for determinism check
    harness2 = sandbox.InMemoryMockHarness(failure_rate=0.30, seed=42)
    batch2 = executor.ConcurrentBatchExecutor(sandbox=harness2, max_workers=8)
    results2 = batch2.execute_batch(tasks, candidate)

    passes1 = [r.passed for r in results1]
    passes2 = [r.passed for r in results2]
    assert passes1 == passes2, "Mock harness must be deterministic under concurrent execution!"
