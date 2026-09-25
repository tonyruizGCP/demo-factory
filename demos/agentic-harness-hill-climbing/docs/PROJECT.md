# Project: Autonomous Evaluation & Hill-Climbing Harness

## Architecture
Autonomous evaluation and hill-climbing harness for agentic coding systems. The system ingests ATIF benchmark suites, executes trials under isolated sandboxes, dynamically applies Bayesian sequential early stopping, diagnoses failure modes via unsupervised trace clustering, and gates candidate promotions through McNemar paired holdout verification within a 7-state lifecycle finite state machine.

### Data Flow
1. **Benchmark Ingestion**: `benchhub/` loads ATIF tasks and creates stratified train/holdout splits.
2. **Trial Execution**: `harbor/` executes agent trials in mock or isolated subprocess sandboxes concurrently.
3. **Early Stopping**: `bayesian/` updates Beta-Binomial posterior superiority and prunes inferior candidates early ($P \le 0.10$).
4. **Trace Mining**: `clustering/` normalizes stack traces and clusters failure logs into archetypes with diagnostic terms.
5. **Holdout Gating**: `lifecycle/holdout_gate.py` evaluates candidate vs baseline on holdout set using McNemar paired test ($b+c < 25$ exact binomial fallback).
6. **State Machine Lifecycle**: `lifecycle/state_machine.py` coordinates the 7-state lifecycle and prevents anti-Goodharting regressions.
7. **Sweep Execution & CLI**: `synthetic/benchmark.py` and `cli.py` provide deterministic synthetic benchmarking and live interactive terminal sweeps.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | ATIF Task Schema & Ingestion | Pydantic schema validation for tasks, environments, and verification specs | M1 | Completed |
| F2 | Stratified Partitioning | Balanced train/holdout splitting across difficulty and behavioral tags | M1 | Completed |
| F3 | Statistical Divergence Verification | Verification of partition parity via Wasserstein and Kolmogorov-Smirnov metrics | M1 | Completed |
| F4 | Trial Telemetry Data Contracts | `TokenSpend`, `TraceSpan`, and `TrialTelemetry` contracts with flexible durations and aliases | M2 | Completed |
| F5 | InMemoryMockHarness | Deterministic seeded mock harness with thread-safe hashing and failure rate controls | M2 | Completed |
| F6 | SubprocessSandbox | Ephemeral workspace isolation, watchdog timeout enforcement, stderr capture | M2 | Completed |
| F7 | Concurrent Batch Executor | Thread-safe batch execution preserving input-output ordering and failure resilience | M2 | Completed |
| F8 | Beta-Binomial Engine | Conjugate Beta-Binomial pass rate modeling with numerical quadrature and large-sample CLT | M3 | Completed |
| F9 | Dynamic Early Stopping | Tri-state stopping controller (`ACCEPT`, `PRUNE`, `CONTINUE`) with warmup and max-evals cap | M3 | Completed |
| F10 | Error Span Extraction | Regex normalization of stack traces (masking 0x..., PIDs, line numbers) and span extraction | M4 | Completed |
| F11 | TF-IDF Trace Vectorizer | Pure-NumPy sublinear TF-IDF vectorizer with n-gram vocabulary and token filtering | M4 | Completed |
| F12 | Archetype Clustering | Pure-NumPy Spherical K-Means clustering producing exemplars and diagnostic terms | M4 | Completed |
| F13 | Paired Holdout Testing | McNemar's paired test with continuity correction and small-sample exact binomial calculation | M5 | Completed |
| F14 | Lifecycle State Machine | 7-state finite state machine (`IDLE` to `TRACE_DIAGNOSIS`) with thread-safe transitions | M5 | Completed |
| F15 | Synthetic Benchmark Suite | Deterministic procedural ATIF task generation with controllable distributions and unique IDs | M6 | Completed |
| F16 | CLI Entrypoint & Packaging | Terminal interactive CLI sweep with live progress table, module entrypoint, and packaging | M6 | Completed |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | BenchHub Data Pipeline | F1, F2, F3: schemas, loader, splitter | None | DONE (146 tests passing) |
| M2 | Harbor Sandbox & Batch Execution | F4, F5, F6, F7: telemetry, sandbox, executor | M1 | DONE (40 tests passing) |
| M3 | Bayesian Sequential Early Stopping | F8, F9: beta-binomial engine, stopping controller | None (pure math/numpy) | DONE (20 tests passing) |
| M4 | Failure Trace Mining & Clustering | F10, F11, F12: trace miner, vectorizer, archetypes | M2 (telemetry schema) | DONE (30 tests passing) |
| M5 | Holdout Verification & Lifecycle FSM | F13, F14: holdout gate, state machine, orchestrator | M2, M3, M4 | DONE (20 tests passing) |
| M6 | Synthetic Benchmarks, CLI & Packaging | F15, F16: benchmark generator, cli.py, __main__.py, packaging | M1-M5 | DONE (20 tests passing) |
| M7 | E2E Test Pass & Hardening | Full 190 E2E tests in tests/e2e/ (Tiers 1-4) passing + adversarial panel | M1-M6 | DONE (100% Pass, Clean Audit) |

---

## Interface Contracts

### M2: Harbor (`harness_optimizer.harbor`)
- `TokenSpend(prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0)`
- `TraceSpan(span_id: str, name: str, start_time: float, end_time: float, duration_ms: float, status: str = "OK", attributes: dict)`
- `TrialTelemetry(trial_id: str, task_id: str, candidate_id: str, passed: bool, exit_code: int = 0, latency_ms: float = 0.0, token_spend: TokenSpend, trace_logs: list, raw_error_message: Optional[str] = None, metadata: dict)`
- `SandboxConfig(timeout_seconds: float = 30.0, timeout_sec: float = 30.0, memory_limit_mb: Optional[int] = 512, env_vars: dict, work_dir: Optional[str], cleanup: bool = True)`
- `BaseSandbox.execute_trial(task: Any, candidate: Any) -> TrialTelemetry`
- `InMemoryMockHarness(failure_rate: float = 0.0, seed: Optional[int] = 42, error_archetypes: Optional[List[str]] = None)`
- `SubprocessSandbox(config: Optional[SandboxConfig] = None)`
- `ConcurrentBatchExecutor(sandbox: Optional[BaseSandbox] = None, max_workers: int = 4)` with `execute_batch(tasks: list, candidate: Any) -> List[TrialTelemetry]`
- Alias: `BatchExecutor = ConcurrentBatchExecutor`

### M3: Bayesian (`harness_optimizer.bayesian`)
- `BetaBinomialModel(alpha: float = 1.0, beta: float = 1.0, prior_alpha: Optional[float] = None, prior_beta: Optional[float] = None)`
  - `update(successes: int = 0, failures: int = 0) -> BetaBinomialModel` (mutates in-place and returns self)
  - `update_from_telemetry(telemetry: TrialTelemetry) -> BetaBinomialModel`
  - `mean() -> float`, `variance() -> float`
  - `posterior_superiority(other: Optional[BetaBinomialModel] = None, *args, **kwargs) -> float`
- `posterior_superiority(...) -> float`
- `StoppingDecision(str, Enum)`: `ACCEPT = "ACCEPT"`, `PRUNE = "PRUNE"`, `CONTINUE = "CONTINUE"`
- `EarlyStoppingController(min_evals: int = 5, max_evals: int = 50, accept_threshold: float = 0.95, prune_threshold: float = 0.10, accept_p: Optional[float] = None, prune_p: Optional[float] = None)`
  - `evaluate(step: int, p_superiority: float) -> StoppingDecision`

### M4: Clustering (`harness_optimizer.clustering`)
- `ErrorSpan(text: str, start_line: Optional[int] = None, end_line: Optional[int] = None, exception_type: Optional[str] = None, message: Optional[str] = None)` with `__contains__` and `__str__`
- `TraceMiner`:
  - `normalize_error(raw: str) -> str`
  - `extract_error_span(text: Optional[str]) -> str`
  - `extract_error_spans(traces: Union[str, List[Any]]) -> List[Any]`
- `TraceVectorizer(ngram_range=(1, 1), max_features=None, force_numpy=False, min_df=1, sublinear_tf=True)`
  - `fit(documents)`, `transform(documents)`, `fit_transform(documents)`
  - `get_feature_names()`, `get_feature_names_out()`, `vocabulary_`
  - Alias: `TFIDFTraceVectorizer = TraceVectorizer`
- `ArchetypeCluster(cluster_id: int, size: int, exemplars: List[str], top_terms: List[str], members: List[str])`
  - Properties: `diagnostic_terms`, `exemplar`, `representative_trace`
- `ClusteredFailureReport(clusters: List[ArchetypeCluster], n_clusters: int, labels: List[int])`
- `ArchetypeClusterer(k_clusters: int = 3, max_iter: int = 100, random_state: Optional[int] = None)`
  - `fit_predict(X, traces=None) -> ClusteredFailureReport`
  - `cluster(traces: List[str]) -> ClusteredFailureReport`
  - `cluster_telemetry(telemetry_list: List[Any]) -> ClusteredFailureReport`

### M5: Lifecycle (`harness_optimizer.lifecycle`)
- `HoldoutDecision(passed: bool, p_value: float, statistic: float = 0.0, contingency_table: dict)` with properties `promoted`, `__bool__`, `__eq__`
- `mcnemar_test(*args, **kwargs)`: returns `(stat, p_val)` for numeric (b, c) inputs, `(p_val, stat)` for sequence inputs
- `HoldoutGate(alpha: float = 0.05)`:
  - `build_contingency_table(baseline_results, candidate_results) -> dict`
  - `exact_binomial(b: int, c: int) -> float`
  - `evaluate_table(b: int, c: int) -> Tuple[float, float]`
  - `evaluate(baseline_results, candidate_results) -> HoldoutDecision`
- `OptimizationState(str, Enum)`: `IDLE`, `BASELINE_RUN`, `CANDIDATE_SEARCH`, `SEQUENTIAL_EXEC`, `HOLDOUT_GATE`, `BASELINE_UPDATE`, `TRACE_DIAGNOSIS`
  - Alias: `LifecycleState = OptimizationState`
- `InvalidStateTransitionError(ValueError)`
  - Alias: `StateTransitionError = InvalidStateTransitionError`
- `OptimizationStateMachine()`:
  - `transition(to_state: Union[OptimizationState, str]) -> OptimizationState`
  - Alias: `transition_to`
  - `reset() -> None`
  - `handle_holdout_decision(decision) -> OptimizationState`
  - `handle_stopping_decision(decision) -> OptimizationState`
  - `diagnose_failures(failed_telemetry) -> ClusteredFailureReport`
  - Alias: `LifecycleStateMachine = OptimizationStateMachine`
- `HillClimbingOrchestrator`

### M6: Synthetic & CLI (`harness_optimizer.synthetic`, `cli.py`)
- `SyntheticBenchmarkGenerator(seed: Optional[int] = None)`
  - `generate(count=None, num_tasks=None, task_count=None, difficulty_distribution=None, tag_distribution=None) -> BenchmarkSuite`
  - Alias: `generate_suite`
- `generate_synthetic_suite(...) -> BenchmarkSuite`
- `cli.py`:
  - `run_sweep(argv: Optional[List[str]] = None) -> int`
  - `main = run_sweep`
  - Arguments: `--tasks` (`-t`), `--seed` (`-s`), `--opt-ratio`, `--min-evals`, `--max-evals`, `--output-format`, `--help`
