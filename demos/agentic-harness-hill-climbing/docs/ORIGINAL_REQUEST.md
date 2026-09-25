# Original User Request

## Initial Request — 2026-09-08T15:11:14Z

Build and complete the standalone reference implementation for the autonomous evaluation and hill-climbing harness for agentic coding systems, picking up from completed Milestone 1 (BenchHub) and driving Milestones 2 through 5 to 100% E2E test passage.

Working directory: /usr/local/google/home/tonyruiz/Desktop/demos/jetski/demos/demo-factory/demos/agentic-harness-hill-climbing
Integrity mode: development

## Prior Work & Current State
- **Milestone 1 Completed**: `harness_optimizer/benchhub/` (`schema.py`, `loader.py`, `splitter.py`) is implemented with 146/146 unit, adversarial, and Monte Carlo tests passing.
- **E2E Test Infrastructure Scaffolded**: 190 opaque-box tests across 4 tiers exist in `tests/e2e/` (Tiers 1–4, covering features F1 through F16) with progressive testability skipping.
- **Goal**: Implement remaining modules (F4–F16) so that all 190 E2E tests and unit suites pass 100%.

## Requirements

### R1. Parallel Trial Execution & Harbor Sandbox Isolation (F4–F7)
- In `harness_optimizer/harbor/`:
  - `telemetry.py` (F4): Implement `TokenSpend`, `TraceSpan`, and `TrialTelemetry` matching E2E contracts in `tests/e2e/test_tier1_features.py` (test_f4_01 to test_f4_05) and `tests/e2e/test_tier2_boundaries.py`.
  - `sandbox.py` (F5, F6): Implement `InMemoryMockHarness` (deterministic seeded RNG, failure rate, synthetic error injection) and `SubprocessSandbox` (ephemeral workspace isolation, watchdog timeout enforcement, non-zero exit handling).
  - `executor.py` (F7): Implement `BatchExecutor` using `ThreadPoolExecutor` or `asyncio` for concurrent trial execution with failure tolerance.

### R2. Bayesian Sequential Early Stopping Engine (F8–F9)
- In `harness_optimizer/bayesian/`:
  - `engine.py` (F8): Latent pass rate modeling $\theta \sim Beta(\alpha, \beta)$ with exact quadrature / numerical methods to compute posterior superiority $P(\theta_c > \theta_b \mid D)$.
  - `stopping.py` (F9): Tri-state stopping controller: Accept $P \ge 0.95$, Prune $P \le 0.10$, Continue otherwise, with configurable `min_evals` warmup and `max_evals` cap.

### R3. Failure Trace Mining & Unsupervised Clustering (F10–F12)
- In `harness_optimizer/clustering/`:
  - `trace_miner.py` (F10): Error log/span extraction, stack frame parsing, and normalization (masking transient memory addresses, PIDs, and line numbers).
  - `vectorizer.py` (F11): Sublinear TF-IDF vectorization with pure-numpy fallback handling.
  - `archetypes.py` (F12): Unsupervised clustering (spherical k-means / cosine) producing operational failure archetypes, top diagnostic terms, and exemplar traces.

### R4. Holdout Verification & State-Machine Lifecycle Orchestrator (F13–F14)
- In `harness_optimizer/lifecycle/`:
  - `holdout_gate.py` (F13): Paired holdout testing using McNemar's paired test with continuity correction and exact binomial calculation.
  - `state_machine.py` (F14): 7-state finite state machine (`IDLE`, `BASELINE_RUN`, `CANDIDATE_SEARCH`, `SEQUENTIAL_EXEC`, `HOLDOUT_GATE`, `BASELINE_UPDATE`, `TRACE_DIAGNOSIS`) enforcing anti-Goodharting gates.

### R5. Synthetic Benchmark Suite, CLI Entrypoint & Packaging (F15–F16)
- In `harness_optimizer/synthetic/`:
  - `benchmark.py` (F15): Deterministic generator producing ATIF tasks with controlled difficulty and behavioral tags.
- Top-level:
  - `cli.py` (F16): Interactive terminal CLI running an end-to-end simulated hill-climbing sweep with live progress.
  - Packaging: Ensure `pyproject.toml` or `requirements.txt` specifies all dependencies cleanly.

## Verification Resources
- Reference implementation base: `/usr/local/google/home/tonyruiz/Desktop/demos/jetski/demos/demo-factory/demos/simbian-cyber-defense-eval/`
- Existing E2E test suite: `/usr/local/google/home/tonyruiz/Desktop/demos/jetski/demos/demo-factory/demos/agentic-harness-hill-climbing/tests/e2e/` (190 test cases)

## Acceptance Criteria

### Execution & Bayesian Stopping
- [ ] `pytest tests/` passes 100% with 0 failures across all unit and E2E suites.
- [ ] All 190 E2E tests in `tests/e2e/` pass cleanly without skips or failures.
- [ ] `InMemoryMockHarness` produces identical trial telemetry given the same random seed.
- [ ] Dynamic Bayesian early stopping prunes inferior candidates ($P \le 0.10$) and advances superior candidates ($P \ge 0.95$).

### Trace Mining & Gating
- [ ] Trace miner extracts normalized failure spans and clusters them into distinct failure archetypes with diagnostic keywords.
- [ ] Lifecycle state machine enforces strict transitions and rejects candidates failing McNemar's holdout gate.

### Interactive Demonstration
- [ ] `python -m harness_optimizer` or `python cli.py` runs a complete end-to-end hill climbing sweep on synthetic benchmarks without external API requirements.

## Follow-up — 2026-09-08T18:44:58Z

The server restarted, halting previous background subagents and cron timers. The user has explicitly requested to revive the swarm.

## Current Project Status
- Progress: Milestones 1, 2, 3, and 4 are implemented in harness_optimizer/ (benchhub/, harbor/, bayesian/, clustering/).
- Test Suite Results: Running pytest tests/ -v produces 276 passed, 56 skipped, 4 failed.
- The 4 Test Failures to Address:
  1. test_f10_04_empty_trace_handling: extract_error_spans("") returned a list of length 1 instead of empty list [].
  2. test_comb_08_f4_f10_failed_telemetry_to_trace_miner: In test_tier3_combinations.py:429, ensure extracted error span contains raw error text or returns formatted span.
  3. test_comb_10_f11_f12_vectorized_traces_to_archetype_clusters: In archetypes.py, ensure clusters have at least 1 top_terms even when vocabulary is small (fallback to cluster terms / exemplars).
  4. test_f2_boundary_split_ratio_extremes_zero_and_one: Boundary ratio handling in splitter.py or test fixture.

## Remaining Scope to Complete
- Milestone 5 (lifecycle/): Implement holdout_gate.py (McNemar's paired test with continuity correction and exact binomial test) and state_machine.py (7-state finite state machine).
- Milestone 6 (synthetic/ & CLI): Implement benchmark.py (synthetic ATIF benchmark suite generator) and cli.py (interactive CLI sweep).
- Milestone 7: Achieve 100% passage across all 190 E2E tests and run final verification.
