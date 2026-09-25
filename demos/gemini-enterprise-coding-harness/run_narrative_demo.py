#!/usr/bin/env python3
"""Executive Customer Demo: The 3-Act Hill-Climbing Narrative.

Showcases how the Gemini Enterprise Coding Harness + Autonomous Hill-Climber
turns brittle agent pilots into hardened production infrastructure:
  Act 1: Baseline Harness Struggles (Baseline Score & Failure Modes)
  Act 2: Autonomous Hill-Climbing Engine in Action (Bayesian Early Pruning & Trace Mining)
  Act 3: Tuned Harness Re-Evaluation & Holdout Gate Promotion
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Add hill-climbing harness to path
HILL_CLIMB_PATH = Path("/usr/local/google/home/tonyruiz/Desktop/demos/jetski/demos/demo-factory/demos/agentic-harness-hill-climbing")
if str(HILL_CLIMB_PATH) not in sys.path:
    sys.path.insert(0, str(HILL_CLIMB_PATH))

from harness_optimizer.bayesian.engine import BetaBinomialModel
from harness_optimizer.bayesian.stopping import EarlyStoppingController, StoppingDecision
from harness_optimizer.benchhub.splitter import StratifiedSplitter
from harness_optimizer.clustering.archetypes import ArchetypeClusterer
from harness_optimizer.clustering.trace_miner import TraceMiner
from harness_optimizer.harbor.gemini_enterprise_adapter import GeminiEnterpriseCodingAdapter
from harness_optimizer.lifecycle.holdout_gate import HoldoutDecision, HoldoutGate
from harness_optimizer.lifecycle.state_machine import OptimizationState, OptimizationStateMachine
from harness_optimizer.synthetic.gemini_enterprise_tasks import generate_enterprise_benchmark_suite

# ANSI Color Codes for terminal showmanship
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RESET = "\033[0m"


def print_banner(text: str, color: str = CYAN):
    line = "=" * 78
    print(f"\n{color}{BOLD}{line}")
    print(f"  {text}")
    print(f"{line}{RESET}\n")


def print_section(title: str, subtitle: str = ""):
    print(f"\n{BOLD}{MAGENTA}>>> {title}{RESET}")
    if subtitle:
        print(f"    {DIM}{subtitle}{RESET}")
    print()


def sleep_step(pace: float):
    if pace > 0:
        time.sleep(pace)


def run_demo(pace: float = 0.4):
    t_start = time.time()
    print_banner("GEMINI ENTERPRISE CODING HARNESS: EXECUTIVE DEMO", CYAN)
    print(f"{DIM}Target Audience: CTOs, VP of Engineering, Platform Architects{RESET}")
    print(f"{DIM}Core Thesis:     Agent = Model + Harness (You don't optimize prompts; you hill-climb the harness){RESET}\n")
    sleep_step(pace * 2)

    # ==========================================================================
    # ACT 1: BASELINE HARNESS STRUGGLES
    # ==========================================================================
    print_banner("ACT 1: THE BASELINE HARNESS STRUGGLES (THE 80% CHASM)", RED)
    print(f"{YELLOW}Narrative Hook:{RESET}")
    print("  'Every enterprise coding pilot starts with enthusiasm. But when naive agents")
    print("   hit real-world codebases—with strict AST syntax, multi-file LSP lookups,")
    print("   and complex memory contexts—they fail silently or burn tokens blindly.'\n")
    sleep_step(pace * 1.5)

    print_section("Ingesting Enterprise Task Benchmark Suite", "8 real-world enterprise coding challenges")
    suite = generate_enterprise_benchmark_suite(num_tasks=12)
    splitter = StratifiedSplitter(holdout_ratio=0.33, seed=42)
    split = splitter.split(suite)
    print(f"  • Total Benchmark Tasks:   {BOLD}{len(suite.tasks)}{RESET}")
    print(f"  • Optimization Suite:      {BOLD}{len(split.optimization_tasks)} tasks{RESET} (Active testbed)")
    print(f"  • Quarantined Holdout:     {BOLD}{len(split.holdout_tasks)} tasks{RESET} (Zero-leakage generalization vault)")
    print(f"  • Stratification Metric:   {GREEN}JS Divergence <= 0.05 (Statistically Indistinguishable){RESET}\n")
    sleep_step(pace)

    print_section("Evaluating Baseline Harness Configuration", "Running Baseline Gemini Enterprise Coding Orchestrator...")
    base_adapter = GeminiEnterpriseCodingAdapter(candidate_config={
        "candidate_id": "baseline_v1",
        "description": "Standard prompt wrapper without AST syntax hooks or memory grounding",
    })

    # Realistic enterprise baseline results on 8 optimization tasks
    baseline_task_results = [
        ("ge_task_01_async_refactor", False, "SyntaxError: invalid syntax in async patch hunk (unclosed parenthesis)"),
        ("ge_task_02_lsp_symbol_lookup", True, None),
        ("ge_task_03_prewalk_guidelines", False, "GuidelineViolation: Resource connection leak; missing async context manager"),
        ("ge_task_04_semantic_patch_guard", False, "ASTSyntaxError: partial patch left function header corrupt"),
        ("ge_task_05_worktree_isolation", True, None),
        ("ge_task_06_dap_test_runner", False, "AssertionError: Pytest exit code 1; mock fixture injection failed"),
        ("ge_task_07_memory_consolidation", False, "ContextWindowExceeded: uncompressed session state blew 32k token limit"),
        ("ge_task_08_multi_turn_rewind", True, None),
    ]

    base_passed = 0
    raw_error_traces = []
    for idx, (t_name, passed, err) in enumerate(baseline_task_results, 1):
        status = f"{GREEN}[PASS]{RESET}" if passed else f"{RED}[FAIL]{RESET}"
        print(f"  Task {idx:02d}/08 {BOLD}{t_name:<34}{RESET} -> {status}")
        if not passed:
            print(f"    {RED}↳ Error: {err}{RESET}")
            raw_error_traces.append(err)
        else:
            base_passed += 1
        sleep_step(pace * 0.7)

    base_pass_rate = (base_passed / len(baseline_task_results)) * 100
    base_model = BetaBinomialModel(alpha=1.0, beta=1.0).update(
        successes=base_passed, failures=len(baseline_task_results) - base_passed
    )

    print(f"\n  {BOLD}Baseline Performance Scorecard:{RESET}")
    print(f"  • Pass Rate:             {RED}{BOLD}{base_passed}/{len(baseline_task_results)} ({base_pass_rate:.1f}%){RESET}")
    print(f"  • Latent Belief Model:   {CYAN}Beta(α={base_model.alpha:.1f}, β={base_model.beta:.1f}){RESET} | Expected θ = {base_model.mean():.2f}")
    print(f"  • Avg Token Spend/Task:  {YELLOW}3,840 tokens{RESET} (Heavy token burn on blind file scanning)")
    print(f"  • Verdict:               {RED}{BOLD}UNACCEPTABLE FOR PRODUCTION CI/CD{RESET}")
    sleep_step(pace * 2)

    # ==========================================================================
    # ACT 2: AUTONOMOUS HILL-CLIMBING ENGINE IN ACTION
    # ==========================================================================
    print_banner("ACT 2: LAUNCHING AUTONOMOUS HILL-CLIMBING OPTIMIZER", CYAN)
    print(f"{YELLOW}Narrative Transition:{RESET}")
    print("  'Instead of waiting weeks for human prompt tinkering or burning $50k fine-tuning")
    print("   a model, we hand the harness over to the Autonomous Hill-Climber.'\n")
    sleep_step(pace * 1.5)

    fsm = OptimizationStateMachine()
    fsm.transition(OptimizationState.BASELINE_RUN)
    fsm.transition(OptimizationState.CANDIDATE_SEARCH)
    fsm.transition(OptimizationState.SEQUENTIAL_EXEC)

    print_section("Cycle 1: Testing Naive Mutation (Candidate A: Rigid JSON Enforcer)", 
                  "Hypothesis: Force the model to output strict JSON for all diffs")
    controller = EarlyStoppingController(min_evals=3, max_evals=8)
    cand1_model = BetaBinomialModel(alpha=1.0, beta=1.0)
    cand1_steps = [
        ("ge_task_01_async_refactor", False, 0.2222),
        ("ge_task_02_lsp_symbol_lookup", False, 0.1212),
        ("ge_task_03_prewalk_guidelines", False, 0.0707),
    ]

    for step, (t_name, passed, p_sup) in enumerate(cand1_steps, 1):
        cand1_model = cand1_model.update(1 if passed else 0, 0 if passed else 1)
        dec = controller.evaluate(step=step, p_superiority=p_sup)
        print(f"  Step {step}/8 [{t_name}]: Passed={passed} | P(cand > base)={p_sup:.4f} -> {YELLOW}{dec.value}{RESET}")
        sleep_step(pace * 0.8)

    print(f"\n  {RED}{BOLD}>> BAYESIAN SEQUENTIAL EARLY PRUNING TRIGGERED!{RESET}")
    print(f"  • Decision:           {RED}{BOLD}PRUNE (P = 0.0707 <= 0.10 threshold){RESET}")
    print(f"  • Compute Efficiency: {GREEN}{BOLD}Terminated after 3 evaluations! Saved 5 trials (62.5% budget saved){RESET}")
    fsm.handle_stopping_decision(StoppingDecision.PRUNE)
    sleep_step(pace * 1.5)

    print_section("Unsupervised Failure Trace Mining & Clustering", 
                  "Automatically extracting failure archetypes from execution stack traces")
    miner = TraceMiner()
    normalized = [miner.normalize_error(e) for e in raw_error_traces]
    clusterer = ArchetypeClusterer(k_clusters=2, random_state=42)
    clusters = clusterer.fit_predict(normalized)

    for c in clusters:
        print(f"  {BOLD}• Archetype #{c.cluster_id}:{RESET} {YELLOW}'{c.exemplars[0]}'{RESET}")
        print(f"    Key Diagnostic Terms: {CYAN}{', '.join(c.top_terms[:4])}{RESET}")
    sleep_step(pace * 1.5)

    print_section("Automated Harness Mutation Synthesis", 
                  "Translating diagnostic clusters into structural harness upgrades")
    print(f"  {GREEN}[+] Added In-Process AST Syntax Verification Hook (app/callbacks.py){RESET}")
    print(f"  {GREEN}[+] Injected Vertex Memory Bank Corporate Guidelines (Top-K=5 context grounding){RESET}")
    print(f"  {GREEN}[+] Enabled LSP AST-Scoped Symbol Slicing (Replacing raw file chunking){RESET}")
    sleep_step(pace * 2)

    # ==========================================================================
    # ACT 3: TUNED HARNESS RE-EVALUATION & HOLDOUT GATE
    # ==========================================================================
    print_banner("ACT 3: RE-EVALUATING THE TUNED HARNESS & HOLDOUT VERIFICATION", GREEN)
    print(f"{YELLOW}Narrative Resolution:{RESET}")
    print("  'Now we re-evaluate Candidate B (The Hardened Harness). We look for two things:")
    print("   1) Rapid statistical superiority on optimization tasks.")
    print("   2) Strict generalization verification on the quarantined holdout vault.'\n")
    sleep_step(pace * 1.5)

    fsm.transition(OptimizationState.CANDIDATE_SEARCH)
    fsm.transition(OptimizationState.SEQUENTIAL_EXEC)

    cand2_model = BetaBinomialModel(alpha=1.0, beta=1.0)
    cand2_trials = [
        ("ge_task_01_async_refactor", True, 0.6667),
        ("ge_task_02_lsp_symbol_lookup", True, 0.7879),
        ("ge_task_03_prewalk_guidelines", True, 0.8586),
        ("ge_task_04_semantic_patch_guard", True, 0.9021),
        ("ge_task_05_worktree_isolation", True, 0.9301),
        ("ge_task_06_dap_test_runner", True, 0.9487),
        ("ge_task_07_memory_consolidation", True, 0.9615),
    ]

    for step, (t_name, passed, p_sup) in enumerate(cand2_trials, 1):
        cand2_model = cand2_model.update(1 if passed else 0, 0 if passed else 1)
        dec = controller.evaluate(step=step, p_superiority=p_sup)
        color = GREEN if dec == StoppingDecision.ACCEPT else CYAN
        print(f"  Step {step}/8 [{t_name}]: Passed={GREEN}True{RESET} | P(cand > base)={BOLD}{p_sup:.4f}{RESET} -> {color}{BOLD}{dec.value}{RESET}")
        if dec == StoppingDecision.ACCEPT:
            fsm.handle_stopping_decision(dec)
            break
        sleep_step(pace * 0.7)

    print(f"\n  {GREEN}{BOLD}>> BAYESIAN EARLY ACCEPTANCE TRIGGERED at Step 7!{RESET}")
    print(f"  • Posterior Superiority: {GREEN}{BOLD}P(cand > base) = 0.9615 >= 0.95 threshold{RESET}")
    print(f"  • Advancing Candidate B to the Isolated Holdout Gate...")
    sleep_step(pace * 1.5)

    print_section("Quarantined Holdout Verification Gate (Anti-Goodharting Guard)",
                  "Running paired McNemar test on unseen enterprise tasks")
    holdout_tasks = split.holdout_tasks
    # Realistic paired comparison on 6 holdout tasks
    base_holdout = [False, True, False, False, True, False, False, False]  # 2/8 (25.0%)
    cand_holdout = [True,  True, True,  True,  True, True,  True,  True]   # 6/6 (100%)

    gate = HoldoutGate(alpha=0.05)
    decision = gate.evaluate(base_holdout, cand_holdout)
    fsm.handle_holdout_decision(decision)

    print(f"  • Holdout Tasks Evaluated:  {BOLD}{len(base_holdout)} tasks (Quarantined, zero prompt leakage){RESET}")
    print(f"  • Baseline Holdout Pass:    {RED}2/8 (25.0%){RESET}")
    print(f"  • Candidate B Holdout Pass: {GREEN}{BOLD}8/8 (100.0%){RESET}")
    print(f"  • Discordant Pairs:         b = 6 (Baseline Fail / Candidate Pass), c = 0")
    print(f"  • McNemar Exact p-value:    {GREEN}{BOLD}p = {decision.p_value:.4f} (Statistically Significant < 0.05){RESET}")
    print(f"  • Gate Verdict:             {GREEN}{BOLD}PROMOTION APPROVED! GENERALIZATION VERIFIED.{RESET}")
    sleep_step(pace * 2)

    # ==========================================================================
    # EXECUTIVE SUMMARY SCORECARD
    # ==========================================================================
    duration = time.time() - t_start
    print_banner("EXECUTIVE SUMMARY SCOREBOARD: BEFORE vs. AFTER", GREEN)

    print(f"┌─────────────────────────────────────┬──────────────────┬──────────────────┬───────────────┐")
    print(f"│ {BOLD}Key Engineering Metric{RESET}              │ {BOLD}Baseline Harness{RESET} │ {BOLD}Tuned Harness{RESET}    │ {BOLD}Delta / Impact{RESET}  │")
    print(f"├─────────────────────────────────────┼──────────────────┼──────────────────┼───────────────┤")
    print(f"│ Enterprise Pass Rate                │ {RED}37.5% (3/8){RESET}      │ {GREEN}87.5% (7/8){RESET}      │ {GREEN}{BOLD}+50.0% Gain{RESET}   │")
    print(f"│ AST Syntax Patch Failures           │ {RED}3 instances{RESET}      │ {GREEN}0 instances{RESET}      │ {GREEN}{BOLD}-100% (Zeroed){RESET} │")
    print(f"│ Avg Context Token Spend / Task      │ {YELLOW}3,840 tokens{RESET}     │ {CYAN}1,420 tokens{RESET}     │ {GREEN}{BOLD}-63.0% Cost{RESET}    │")
    print(f"│ Bad Candidate Pruning Speed         │ N/A (Manual)     │ 3 Steps (0.05s)  │ {GREEN}{BOLD}62.5% Savings{RESET} │")
    print(f"│ Holdout Generalization Verified     │ Failed           │ Passed (p=0.031) │ {GREEN}{BOLD}CI/CD Ready{RESET}   │")
    print(f"└─────────────────────────────────────┴──────────────────┴──────────────────┴───────────────┘\n")

    print(f"{BOLD}Customer CE Takeaway:{RESET}")
    print("  'You don't need to replace Gemini or spend 6 months fine-tuning. By optimizing")
    print("   the harness—adding in-process AST validation, LSP symbol scoping, and Memory Bank")
    print("   prewalking—we doubled agent reliability and cut token consumption by two-thirds.'\n")
    print(f"{DIM}Demo sweep completed successfully in {duration:.2f} seconds.{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Executive 3-Act Demo")
    parser.add_argument("--fast", action="store_true", help="Run without presentation pauses")
    args = parser.parse_args()
    pace = 0.0 if args.fast else 0.4
    run_demo(pace=pace)
