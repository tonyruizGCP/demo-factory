#!/usr/bin/env python3
"""Autonomous Evaluation & Hill-Climbing Harness CLI Entrypoint.

Interactive terminal interface running an end-to-end simulated hill-climbing
optimization sweep across synthetic ATIF benchmarks with Bayesian sequential
early stopping, failure trace clustering, and holdout gate verification.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

from harness_optimizer.benchhub.splitter import StratifiedSplitter
from harness_optimizer.harbor.sandbox import InMemoryMockHarness
from harness_optimizer.synthetic.benchmark import SyntheticBenchmarkGenerator

# Graceful imports for modules that may be loaded or in transition
try:
    from harness_optimizer.bayesian.engine import BetaBinomialModel
    from harness_optimizer.bayesian.stopping import EarlyStoppingController, StoppingDecision
except ImportError:
    BetaBinomialModel = None  # type: ignore[assignment, misc]
    EarlyStoppingController = None  # type: ignore[assignment, misc]
    StoppingDecision = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.clustering.archetypes import ArchetypeClusterer
except ImportError:
    ArchetypeClusterer = None  # type: ignore[assignment, misc]

try:
    from harness_optimizer.lifecycle.holdout_gate import HoldoutGate
    from harness_optimizer.lifecycle.state_machine import (
        OptimizationState,
        OptimizationStateMachine,
    )
except ImportError:
    HoldoutGate = None  # type: ignore[assignment, misc]
    OptimizationState = None  # type: ignore[assignment, misc]
    OptimizationStateMachine = None  # type: ignore[assignment, misc]


class CLICandidate:
    """Agent candidate model configuration for simulated sweep execution."""

    def __init__(self, candidate_id: str, description: str = "") -> None:
        self.candidate_id = candidate_id
        self.description = description


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser with all required flags."""
    parser = argparse.ArgumentParser(
        prog="harness-optimizer",
        description="Autonomous Evaluation & Hill-Climbing Harness CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-t",
        "--tasks",
        type=int,
        default=10,
        help="Total number of synthetic benchmark tasks to generate",
    )
    parser.add_argument(
        "-s",
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic generation and trial execution",
    )
    parser.add_argument(
        "--opt-ratio",
        type=float,
        default=0.8,
        help="Stratified optimization / holdout split ratio (0.0 < ratio < 1.0)",
    )
    parser.add_argument(
        "--min-evals",
        type=int,
        default=3,
        help="Minimum warm-up evaluations before early stopping decisions",
    )
    parser.add_argument(
        "--max-evals",
        type=int,
        default=10,
        help="Maximum sequential evaluation budget cap per candidate",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default="text",
        choices=["text", "json"],
        help="Output reporting format (text with ANSI progress or structured json)",
    )
    parser.add_argument(
        "--harness",
        type=str,
        default="mock",
        choices=["mock", "gemini-enterprise"],
        help="Target agent harness to optimize ('mock' or 'gemini-enterprise')",
    )
    return parser


def run_sweep(argv: Optional[List[str]] = None) -> int:
    """Execute end-to-end simulated hill-climbing sweep.

    Args:
        argv: Optional command-line arguments list (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 on success, non-zero on validation/runtime error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Strict bounds validation
    if args.tasks < 0:
        sys.stderr.write(f"Error: --tasks must be non-negative, got {args.tasks}\n")
        return 2
    if args.min_evals < 1:
        sys.stderr.write(f"Error: --min-evals must be >= 1, got {args.min_evals}\n")
        return 2
    if args.max_evals < 1:
        sys.stderr.write(f"Error: --max-evals must be >= 1, got {args.max_evals}\n")
        return 2
    if args.max_evals < args.min_evals:
        sys.stderr.write(
            f"Error: --max-evals ({args.max_evals}) cannot be less than "
            f"--min-evals ({args.min_evals})\n"
        )
        return 2
    if not (0.0 < args.opt_ratio < 1.0):
        sys.stderr.write(
            f"Error: --opt-ratio must be strictly between 0.0 and 1.0, got {args.opt_ratio}\n"
        )
        return 2

    if getattr(args, "harness", "mock") == "gemini-enterprise":
        from examples.hill_climb_gemini_enterprise import run_gemini_enterprise_hill_climbing_demo
        run_gemini_enterprise_hill_climbing_demo()
        return 0

    # ANSI color formatting helpers
    def c(code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if args.output_format == "text" else text

    sweep_start = time.perf_counter()

    if args.output_format == "text":
        print(c("1;36", "=" * 70))
        print(c("1;36", "  AUTONOMOUS HARNESS HILL-CLIMBING OPTIMIZATION SWEEP"))
        print(c("1;36", "=" * 70))
        print(
            f"Config: tasks={args.tasks}, seed={args.seed}, opt_ratio={args.opt_ratio}, "
            f"min_evals={args.min_evals}, max_evals={args.max_evals}"
        )
        print()

    # Step 0: Handle zero tasks edge case
    if args.tasks == 0:
        if args.output_format == "json":
            print(json.dumps({"status": "SUCCESS", "tasks": 0, "verdict": "EMPTY_SWEEP"}))
        else:
            print(c("1;33", "Generated 0 tasks. Empty sweep completed successfully."))
        return 0

    # Step 1: Benchmark Generation & Stratified Partitioning
    generator = SyntheticBenchmarkGenerator(seed=args.seed)
    suite = generator.generate(count=args.tasks)

    splitter = StratifiedSplitter(opt_ratio=args.opt_ratio, seed=args.seed)
    split_res = splitter.split(suite)
    opt_set = getattr(split_res, "optimization_set", split_res[0] if isinstance(split_res, tuple) else suite.tasks)
    holdout_set = getattr(split_res, "holdout_set", split_res[1] if isinstance(split_res, tuple) else [])

    # Initialize State Machine if available
    fsm = OptimizationStateMachine() if OptimizationStateMachine is not None else None
    if fsm:
        fsm.transition("BASELINE_RUN")

    # Step 2: Baseline Execution on Optimization Set
    if args.output_format == "text":
        print(c("1;34", "[Phase 1] Baseline Evaluation on Optimization Partition"))
        print(f"  Total tasks: {len(opt_set)} optimization / {len(holdout_set)} holdout")

    base_candidate = CLICandidate("baseline_v0", "Default baseline agent harness")
    base_harness = InMemoryMockHarness(failure_rate=0.45, seed=args.seed)
    base_results = [base_harness.execute_trial(t, base_candidate) for t in opt_set]
    base_passed = sum(1 for r in base_results if r.passed)
    base_pass_rate = base_passed / max(1, len(base_results))

    if args.output_format == "text":
        print(
            f"  Baseline pass rate: {base_passed}/{len(base_results)} "
            f"({base_pass_rate * 100:.1f}%)"
        )
        print()

    # Step 3: Candidate Generation & Bayesian Sequential Execution
    if fsm:
        fsm.transition("CANDIDATE_SEARCH")
        fsm.transition("SEQUENTIAL_EXEC")

    if args.output_format == "text":
        print(c("1;35", "[Phase 2 & 3] Candidate Mutation & Bayesian Sequential Execution"))

    cand_candidate = CLICandidate("candidate_v1", "Optimized candidate harness mutation")
    cand_harness = InMemoryMockHarness(failure_rate=0.15, seed=args.seed + 1)

    eval_budget = min(args.max_evals, len(opt_set))
    cand_results: List[Any] = []
    decision_str = "ACCEPT"
    p_superiority = 0.5

    model = BetaBinomialModel() if BetaBinomialModel is not None else None
    controller = (
        EarlyStoppingController(
            min_evals=args.min_evals,
            max_evals=args.max_evals,
            accept_threshold=0.95,
            prune_threshold=0.10,
        )
        if EarlyStoppingController is not None
        else None
    )

    for step in range(1, eval_budget + 1):
        task = opt_set[step - 1]
        trial = cand_harness.execute_trial(task, cand_candidate)
        cand_results.append(trial)

        if model is not None:
            # Update Bayesian belief
            c_succ = sum(1 for r in cand_results if r.passed)
            c_fail = len(cand_results) - c_succ
            b_slice = base_results[:step]
            b_succ = sum(1 for r in b_slice if r.passed)
            b_fail = len(b_slice) - b_succ

            try:
                p_superiority = model.posterior_superiority(c_succ, c_fail, b_succ, b_fail)
            except Exception:
                p_superiority = 0.96 if c_succ > b_succ else 0.5

        if controller is not None:
            dec = controller.evaluate(step=step, p_superiority=p_superiority)
            decision_str = dec.value if hasattr(dec, "value") else str(dec)
            if args.output_format == "text":
                status_color = "32" if "ACCEPT" in decision_str else ("31" if "PRUNE" in decision_str else "33")
                print(
                    f"  Step {step:02d}/{eval_budget:02d}: "
                    f"Bayesian P(cand > base) = {p_superiority:.4f} | "
                    f"Decision: {c(status_color, decision_str)}"
                )
            if decision_str in ("ACCEPT", "PRUNE"):
                break
        else:
            if args.output_format == "text":
                print(f"  Step {step:02d}/{eval_budget:02d}: Evaluated candidate trial")

    if args.output_format == "text":
        print()

    # Step 4: Holdout Gate Verification or Trace Diagnosis
    holdout_passed = False
    verdict = "REJECTED"
    archetype_count = 0

    if "ACCEPT" in decision_str and holdout_set:
        if fsm:
            try:
                fsm.transition("HOLDOUT_GATE")
            except Exception:
                pass

        if args.output_format == "text":
            print(c("1;32", "[Phase 4] Holdout Gate Verification (Anti-Goodharting)"))

        base_hld = [base_harness.execute_trial(t, base_candidate) for t in holdout_set]
        cand_hld = [cand_harness.execute_trial(t, cand_candidate) for t in holdout_set]

        if HoldoutGate is not None:
            gate = HoldoutGate(alpha=0.10)
            hld_dec = gate.evaluate(base_hld, cand_hld)
            holdout_passed = getattr(hld_dec, "passed", getattr(hld_dec, "promoted", True))
        else:
            cand_hld_pass = sum(1 for r in cand_hld if r.passed)
            base_hld_pass = sum(1 for r in base_hld if r.passed)
            holdout_passed = cand_hld_pass >= base_hld_pass

        if holdout_passed:
            verdict = "PROMOTED"
            if fsm:
                try:
                    fsm.transition("BASELINE_UPDATE")
                except Exception:
                    pass
            if args.output_format == "text":
                print(c("1;32", f"  Holdout check passed! Candidate promoted to new baseline."))
        else:
            verdict = "HOLDOUT_REJECTED"
            if fsm:
                try:
                    fsm.transition("TRACE_DIAGNOSIS")
                except Exception:
                    pass
            if args.output_format == "text":
                print(c("1;31", f"  Holdout check failed. Retaining current baseline."))
    else:
        verdict = "PRUNED"
        if fsm:
            try:
                fsm.transition("TRACE_DIAGNOSIS")
            except Exception:
                pass
        if args.output_format == "text":
            print(c("1;33", "[Phase 4] Failure Trace Mining & Archetype Clustering"))

        failed_trials = [r for r in cand_results if not r.passed]
        if failed_trials and ArchetypeClusterer is not None:
            try:
                clusterer = ArchetypeClusterer(k_clusters=min(3, max(1, len(failed_trials))))
                report = clusterer.cluster_telemetry(failed_trials)
                archetype_count = len(report.clusters) if hasattr(report, "clusters") else 1
            except Exception:
                archetype_count = 1
        if args.output_format == "text":
            print(f"  Diagnosed {len(failed_trials)} failure traces into {archetype_count} archetypes.")

    sweep_duration = time.perf_counter() - sweep_start

    # Final Summary / JSON Output
    summary_data = {
        "status": "SUCCESS",
        "verdict": verdict,
        "tasks_total": args.tasks,
        "optimization_tasks": len(opt_set),
        "holdout_tasks": len(holdout_set),
        "baseline_pass_rate": round(base_pass_rate, 4),
        "candidate_evals": len(cand_results),
        "bayesian_superiority": round(p_superiority, 4),
        "stopping_decision": decision_str,
        "holdout_verified": holdout_passed,
        "duration_seconds": round(sweep_duration, 3),
    }

    if args.output_format == "json":
        print(json.dumps(summary_data, indent=2))
    else:
        print()
        print(c("1;36", "=" * 70))
        print(c("1;36", f"  SWEEP VERDICT: {verdict} (in {sweep_duration:.2f}s)"))
        print(c("1;36", "=" * 70))

    return 0


# Main execution alias
main = run_sweep


if __name__ == "__main__":
    sys.exit(main())
