# End-to-End Test Infrastructure Specification

This document defines the architecture, methodology, feature coverage, execution model, and thresholds for the End-to-End (E2E) Test Suite of the **Autonomous Evaluation & Hill-Climbing Harness for Agentic Coding Systems**.

---

## 1. Test Philosophy

The E2E test suite adheres to a rigorous, opaque-box, requirement-driven philosophy:

1. **Opaque-Box Verification**: Tests interact exclusively with public contracts, module entrypoints, and command-line interfaces. Internal private states and implementation details are treated as opaque to ensure tests validate contractual behavior rather than accidental implementation side effects.
2. **Requirement-Driven Derivation**: Every test case is traced directly to formal functional requirements specified in `ORIGINAL_REQUEST.md` (R1 through R6) and the `PROJECT.md` Feature Inventory (Features F1 through F16).
3. **Progressive Testability & Graceful Skipping**: Tests are self-contained and isolated. When running intermediate milestones, unimplemented components gracefully skip via informative markers rather than throwing unhandled import crashes, while executing fully and deterministically once the respective milestone components are in place.
4. **Adversarial & Numerical Integrity**: Statistical engines, early stopping boundaries, and holdout tests are verified under extreme, boundary, and pathological conditions (e.g., zero evaluations, 100% pass/fail rates, tie scenarios, continuity corrections) to prevent regression, false promotions, and reward hacking (Goodharting).

---

## 2. 4-Tier Testing Methodology

The test suite is partitioned into four complementary tiers:

```
+-----------------------------------------------------------------------------------+
|                        Tier 1: Category-Partition Tests                           |
|       (Standalone requirement verification for every feature F1 to F16, >=5/feat)  |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                       Tier 2: Boundary Value Analysis                             |
|      (Pathological zero-bounds, singletons, extreme probabilities, timeout caps)   |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                     Tier 3: Pairwise Combinatorial Tests                          |
|        (Cross-module interface contracts: Ingestion ↔ Splitter ↔ Sandbox ↔ Bayes) |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                  Tier 4: Realistic Application Workloads                          |
|         (Full end-to-end hill-climbing cycles, Goodhart holdout rejection, CLI)    |
+-----------------------------------------------------------------------------------+
```

- **Tier 1: Category-Partition Tests (`tests/e2e/test_tier1_features.py`)**:
  Exhaustively verifies every discrete capability across all 16 features (F1 through F16) with at least 5 standalone test cases per feature (minimum 80 test cases).
- **Tier 2: Boundary Value Analysis (`tests/e2e/test_tier2_boundaries.py`)**:
  Validates edge and corner cases, including empty suites, singleton strata, numerical stability at 0/0 and 100/100, watchdog timeout caps, and minimum warmup limits (minimum 80 test cases).
- **Tier 3: Pairwise Combinatorial Tests (`tests/e2e/test_tier3_combinations.py`)**:
  Validates pairwise cross-module contracts and state interactions between Ingestion, Execution, Bayesian Stopping, Trace Clustering, and Holdout Gating (minimum 16 test cases).
- **Tier 4: Real-World Application Workloads (`tests/e2e/test_tier4_scenarios.py`)**:
  Validates full-scale, end-to-end lifecycle workflows: baseline establishment, candidate evaluation, early pruning, candidate promotion, holdout rejection of overfit candidates, and CLI reporting (minimum 8 test cases).

---

## 3. Feature Inventory Table (F1 through F16)

| ID | Feature Name | Core Functional Responsibility | Source Requirement | Target Module |
|---|---|---|---|---|
| **F1** | ATIF Task Schema & Ingestion | Pydantic V2 models for ATIF tasks, verification specs, and behavioral tags (`tool_selection`, `multi_step_retrieval`, `state_mutation`, `constraint_adherence`) | R1 | `harness_optimizer.benchhub.schema`, `loader` |
| **F2** | Multidimensional Stratified Splitting | Partitioning into Optimization (70%) and Holdout (30%) sets preserving joint distributions across tags and difficulty with zero task leakage | R1 | `harness_optimizer.benchhub.splitter` |
| **F3** | Statistical Divergence Verification | Jensen-Shannon divergence and Chi-square goodness-of-fit metrics validating partition statistical balance | R1 | `harness_optimizer.benchhub.splitter` |
| **F4** | Trial Telemetry & Data Contracts | Telemetry capturing pass/fail status, latency ms, token spend, exit codes, and structured trace logs | R3 | `harness_optimizer.harbor.telemetry` |
| **F5** | InMemoryMockHarness | Fast, deterministic mock execution harness with seeded RNG, controlled failure rates, and synthetic error injection | R3 | `harness_optimizer.harbor.sandbox` |
| **F6** | Subprocess Sandbox Isolation | Process execution sandbox with resource limits, ephemeral workspace isolation, and watchdog timeouts | R3 | `harness_optimizer.harbor.sandbox`, `config` |
| **F7** | Concurrent Batch Executor | ThreadPoolExecutor running parallel trials with streaming task execution, mapping preservation, and failure tolerance | R3 | `harness_optimizer.harbor.executor` |
| **F8** | Beta-Binomial Conjugate Engine | Bayesian latent pass rate modeling $\theta \sim Beta(\alpha, \beta)$ with exact quadrature, posterior superiority $P(\theta_c > \theta_b \mid D)$, and numerical stability | R2 | `harness_optimizer.bayesian.engine` |
| **F9** | Dynamic Bayesian Early Stopping | Tri-state stopping controller: Accept $P \ge 0.95$, Prune $P \le 0.10$, Continue with warmup guard and hard max evals | R2 | `harness_optimizer.bayesian.stopping` |
| **F10** | Error Span & Trace Extraction | Stack frame parsing, error normalization (removing transient memory addresses and line numbers), and span boundary detection | R4 | `harness_optimizer.clustering.trace_miner` |
| **F11** | TF-IDF Trace Vectorizer | Sublinear N-gram TF-IDF vectorization with pure-numpy fallback handling and token filtering | R4 | `harness_optimizer.clustering.vectorizer` |
| **F12** | Unsupervised Archetype Clustering | Spherical K-means clustering into operational failure archetypes with diagnostic keyword extraction and exemplars | R4 | `harness_optimizer.clustering.archetypes` |
| **F13** | Paired Holdout Testing (McNemar) | McNemar's paired binary test with continuity correction and exact binomial test for holdout validation | R5 | `harness_optimizer.lifecycle.holdout_gate` |
| **F14** | State-Machine Lifecycle Orchestrator | 7-state finite state machine (`IDLE`, `BASELINE_RUN`, `CANDIDATE_SEARCH`, `SEQUENTIAL_EXEC`, `HOLDOUT_GATE`, `BASELINE_UPDATE`, `TRACE_DIAGNOSIS`) with strict transition guards | R5 | `harness_optimizer.lifecycle.state_machine` |
| **F15** | Synthetic Benchmark Generator | Deterministic task suite generator creating diverse ATIF tasks with controlled ground truth difficulty and tags | R6 | `harness_optimizer.synthetic.benchmark` |
| **F16** | CLI Entrypoint & Packaging | Rich/ANSI interactive terminal CLI, argument parsing, synthetic sweep execution, and packaging importability | R6 | `cli.py`, `harness_optimizer` |

---

## 4. Test Architecture & Directory Layout

The tests are organized cleanly under `tests/` and co-located with the target package:

```
demos/agentic-harness-hill-climbing/
├── TEST_INFRA.md                          # Test infrastructure specification (this file)
├── pyproject.toml                         # Packaging and pytest configuration
├── harness_optimizer/                     # Core package modules
│   ├── benchhub/                          # F1, F2, F3
│   ├── harbor/                            # F4, F5, F6, F7
│   ├── bayesian/                          # F8, F9
│   ├── clustering/                        # F10, F11, F12
│   ├── lifecycle/                         # F13, F14
│   └── synthetic/                         # F15
├── cli.py                                 # F16
└── tests/
    ├── __init__.py
    ├── conftest.py                        # Common fixtures, seed generators, synthetic suites
    └── e2e/
        ├── __init__.py
        ├── test_tier1_features.py         # Tier 1: Category-Partition (F1-F16 >=5/feat, >=80 total)
        ├── test_tier2_boundaries.py       # Tier 2: Boundary Value Analysis (>=80 total)
        ├── test_tier3_combinations.py     # Tier 3: Pairwise Combinatorial (>=16 total)
        └── test_tier4_scenarios.py        # Tier 4: Real-World Scenarios (>=8 total)
```

### Test Runner Invocation

To invoke the test suite:

```bash
# Run the entire E2E test suite
pytest tests/e2e/ -v

# Run Tier 1 feature verification exclusively
pytest tests/e2e/test_tier1_features.py -v

# Run specific feature tests (e.g. F8 Beta-Binomial)
pytest tests/e2e/test_tier1_features.py -k "test_f8" -v

# Run with syntax validation only
python3 -m py_compile tests/e2e/test_tier1_features.py
```

### Pass / Fail Semantics

- **PASS**: Test assertions verify expected values derived mathematically or from the formal specification.
- **SKIP**: Feature module not yet present during progressive milestone delivery (with clear indication of missing module).
- **FAIL**: Contractual violation, divergence exceeding threshold, state transition violation, non-zero exit code on valid task, or leakage between partitions.

---

## 5. Real-World Application Scenarios (Tier 4)

Tier 4 exercises complete real-world scenarios representing realistic agentic hill-climbing cycles:

1. **Scenario 1: Superior Candidate Hill-Climbing Promotion**:
   A candidate model superior to the baseline ($+25\%$ pass rate) evaluates sequentially on the Optimization Set, triggers early stopping acceptance ($P \ge 0.95$), passes McNemar's paired test on the Holdout Set ($p < 0.05$), and updates the active baseline.
2. **Scenario 2: Inferior Candidate Early Pruning & Diagnosis**:
   An underperforming candidate model ($-30\%$ pass rate) is evaluated sequentially, triggers early pruning at $P \le 0.10$ after minimum warmup evals, halts trial execution without evaluating the holdout set, and routes failed traces to `TRACE_DIAGNOSIS` for clustering.
3. **Scenario 3: Goodhart Anti-Overfitting Rejection**:
   A candidate model specifically overfit to the Optimization Set (100% pass on Optimization, but regression on Holdout Set) successfully clears early stopping on the Optimization Set, but is strictly rejected by the Holdout Gate via McNemar's paired test, preventing active baseline corruption.
4. **Scenario 4: Non-Stationary Drift & Tie Resolution**:
   A candidate model with statistically indistinguishable performance from the baseline ($P \approx 0.50$) consumes trials up to `max_evals` without reaching early acceptance, followed by holdout evaluation that fails to reject the null hypothesis, leaving the baseline intact.
5. **Scenario 5: Multi-Cluster Trace Mining Under Heterogeneous Failures**:
   A batch of 50 failed trials containing mixed error types (context overflow, timeout, syntax error, missing artifact) is ingested by the trace miner, successfully partitioned into distinct archetype clusters, and outputs top diagnostic terms and representative exemplars.
6. **Scenario 6: End-to-End CLI Sweep Execution**:
   A full end-to-end execution invoked via the CLI (`python cli.py --tasks 20 --seed 42 --opt-ratio 0.7`) executes synthetic task generation, baseline run, candidate evaluation, and prints structured ANSI terminal reports with exit code 0.
7. **Scenario 7: High-Concurrency Sandbox Trial Execution**:
   Concurrent execution of a batch of 30 tasks with 8 parallel worker threads in `ConcurrentBatchExecutor` completes deterministically without race conditions or memory corruption.
8. **Scenario 8: Zero-Leakage Data Partitioning with Extreme Strata Skew**:
   A complex benchmark suite with highly skewed multi-label tag combinations and rare singletons undergoes stratified splitting, strictly preserving mutual exclusivity ($\mathcal{D}_{\text{opt}} \cap \mathcal{D}_{\text{hold}} = \emptyset$) and passing Chi-square marginal distribution balance tests.

---

## 6. Coverage Thresholds

| Test Tier | Focus / Scope | Minimum Count | Verification Target |
|---|---|---|---|
| **Tier 1** | Category-Partition (Features F1 through F16) | $\ge 80$ ($5 \times 16$) | Public contracts, individual functional requirements |
| **Tier 2** | Boundary Value Analysis & Extreme Inputs | $\ge 80$ | Zero bounds, singletons, extreme probabilities, timeouts |
| **Tier 3** | Pairwise Combinatorial Interactions | $\ge 16$ | Cross-module interfaces and lifecycle handoffs |
| **Tier 4** | Real-World Application Workloads | $\ge 8$ | End-to-end hill-climbing cycles, Goodharting guards, CLI |
| **Total** | **Full E2E Test Suite** | **$\ge 184$** | **100% requirements coverage across R1–R6** |
