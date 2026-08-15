#!/usr/bin/env python3
"""Command Line Interface for Cyber Defense Benchmark Evaluations.

Integrates BenchHub dataset curation, Harbor sandboxed execution,
and Google Antigravity & Open Code agent harnesses powered by Gemini 3.7 Flash.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchhub.curator import BenchHubCurator
from core.mitre import get_all_tactics, get_tactic_metadata
from evaluation.evaluator import CyberDefenseEvaluator
from evaluation.report_generator import ReportGenerator


def format_status(passed: bool) -> str:
    """Format pass/fail status with ANSI colors."""
    if passed:
        return "\033[92m✔ PASSED\033[0m"
    return "\033[91m✖ FAILED\033[0m"


def format_header(title: str) -> None:
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  \033[1;36m{title}\033[0m")
    print("=" * 80)


def cmd_list_scenarios(args: argparse.Namespace) -> None:
    """List all available Cyber Defense Benchmark scenarios."""
    curator = BenchHubCurator()
    scenarios = curator.list_scenarios()

    format_header("BENCHHUB CYBER DEFENSE BENCHMARK SCENARIOS")
    print(f"{'ID':<25} {'Title':<45} {'Family':<15} {'Difficulty':<15} {'Events':<8}")
    print("-" * 110)

    for sc in scenarios:
        print(f"{sc.id:<25} {sc.title[:43]:<45} {sc.attack_family:<15} {sc.difficulty:<15} {len(sc.events):<8}")
    print(f"\nTotal Scenarios in Catalog: {len(scenarios)}\n")


def cmd_list_slices(args: argparse.Namespace) -> None:
    """List available BenchHub dataset curation slices."""
    curator = BenchHubCurator()
    slices = curator.list_slices()

    format_header("BENCHHUB CURATION DATASET SLICES")
    print(f"{'Slice ID':<28} {'Name':<35} {'Tags':<25}")
    print("-" * 90)

    for sl in slices:
        tags_str = ", ".join(sl.tags)
        print(f"{sl.slice_id:<28} {sl.name:<35} {tags_str:<25}")
        print(f"  └─ \033[90m{sl.description}\033[0m\n")


def cmd_list_skills(args: argparse.Namespace) -> None:
    """List all registered agent skills and their weights."""
    from core.skills_loader import SkillsRegistry
    registry = SkillsRegistry()
    skills = registry.get_skills_list()

    format_header("REGISTERED HARNESS SKILLS (AGENTS.md)")
    print(f"{'Skill ID':<30} {'Role':<30} {'Weight':<8} {'Description':<40}")
    print("-" * 110)

    for sk in skills:
        print(f"{sk['skill_id']:<30} {sk['role']:<30} {sk['weight']:<8.1f} {sk['description'][:38]:<40}")
    print(f"\nTotal Registered Skills: {len(skills)}\n")


def cmd_run_eval(args: argparse.Namespace) -> None:
    """Execute a benchmark evaluation on a scenario."""
    evaluator = CyberDefenseEvaluator()

    format_header(f"RUNNING EVALUATION: {args.scenario} | HARNESS: {args.harness.upper()}")
    print(f"▶ Model: {args.model} | Thinking Budget: {args.thinking_budget} tokens | Live LLM: {args.live}")
    print(f"▶ Harbor Sandbox Mode: {args.sandbox_mode}")

    try:
        summary = evaluator.run_evaluation(
            scenario_id=args.scenario,
            harness_name=args.harness,
            model_name=args.model,
            thinking_budget=args.thinking_budget,
            use_live_llm=args.live,
            harbor_sandbox_mode=args.sandbox_mode,
            benchhub_slice=args.slice or "custom",
        )
    except Exception as e:
        print(f"\n\033[91m[Error] Evaluation failed: {e}\033[0m")
        sys.exit(1)

    m = summary.metrics
    t = summary.trajectory

    print("\n" + "-" * 80)
    print(f"🎯 SIMBIAN BENCHMARK VERDICT: {format_status(m.simbian_pass_status)}")
    print(f"   {m.summary_verdict}")
    print("-" * 80)

    print(f"\n📊 AGGREGATE PERFORMANCE METRICS:")
    print(f"  • Overall Recall:         \033[1m{m.overall_recall * 100:.1f}%\033[0m (Target: >= 50% per tactic)")
    print(f"  • Overall Precision:      \033[1m{m.overall_precision * 100:.1f}%\033[0m")
    print(f"  • Overall F1 Score:       \033[1m{m.overall_f1 * 100:.1f}%\033[0m")
    print(f"  • MITRE Chain Coverage:   \033[1m{m.mitre_chain_coverage * 100:.1f}%\033[0m")
    print(f"  • Query Efficiency:       \033[1m{m.query_efficiency_score}\033[0m true positives / query")
    print(f"  • False Discovery Rate:   \033[1m{m.false_discovery_rate * 100:.1f}%\033[0m")
    print(f"  • Total Trajectory Steps: \033[1m{t.total_steps}\033[0m ({t.execution_time_seconds:.2f}s wall-clock)")

    print("\n📋 12-TACTIC MITRE ATT&CK BREAKDOWN:")
    print(f"{'Tactic':<25} {'GroundTruth':<14} {'TP':<6} {'FP':<6} {'Recall':<10} {'Precision':<12} {'Simbian Bar'}")
    print("-" * 85)

    for tactic_val, score in m.tactic_scores.items():
        meta = get_tactic_metadata(score.tactic)
        name = meta.get("name", tactic_val)
        pass_str = format_status(score.passed_simbian_bar)
        rec_str = f"{score.recall * 100:.1f}%"
        prec_str = f"{score.precision * 100:.1f}%"
        print(f"{name:<25} {score.ground_truth_count:<14} {score.true_positives:<6} {score.false_positives:<6} {rec_str:<10} {prec_str:<12} {pass_str}")

    if args.output:
        out_path = Path(args.output)
        if out_path.suffix.lower() == ".json":
            content = ReportGenerator.generate_json_report(summary)
        else:
            content = ReportGenerator.generate_markdown_report(summary)
        out_path.write_text(content, encoding="utf-8")
        print(f"\n📁 Report saved to: {out_path.resolve()}")


def cmd_compare_harnesses(args: argparse.Namespace) -> None:
    """Run a multi-harness comparison (Antigravity vs Open Code vs Baseline)."""
    evaluator = CyberDefenseEvaluator()
    harnesses = ["antigravity", "opencode", "baseline"]
    summaries = []

    format_header(f"MULTI-HARNESS BENCHMARK COMPARISON ON: {args.scenario}")
    print("Evaluating Google Antigravity, Open Code, and Single-Turn Baseline...\n")

    for h in harnesses:
        print(f"▶ Running harness: \033[1m{h.upper()}\033[0m...")
        summary = evaluator.run_evaluation(
            scenario_id=args.scenario,
            harness_name=h,
            model_name=args.model,
            thinking_budget=args.thinking_budget,
            use_live_llm=args.live,
            harbor_sandbox_mode="local-isolated",
        )
        summaries.append(summary)

    format_header("COMPARATIVE BENCHMARK RESULTS")
    print(f"{'Harness':<30} {'Recall':<10} {'Precision':<12} {'F1':<10} {'Chain Cov':<12} {'Queries':<10} {'Simbian Pass'}")
    print("-" * 95)

    for s in summaries:
        m = s.metrics
        t = s.trajectory
        pass_str = format_status(m.simbian_pass_status)
        print(
            f"{s.agent_harness:<30} "
            f"{m.overall_recall * 100:>5.1f}%    "
            f"{m.overall_precision * 100:>5.1f}%      "
            f"{m.overall_f1 * 100:>5.1f}%    "
            f"{m.mitre_chain_coverage * 100:>5.1f}%      "
            f"{t.total_queries:<10} "
            f"{pass_str}"
        )
    print("\n")


def cmd_history(args: argparse.Namespace) -> None:
    """List historical evaluation runs."""
    evaluator = CyberDefenseEvaluator()
    history = evaluator.list_history()

    format_header("EVALUATION RUN HISTORY")
    if not history:
        print("No past evaluation runs recorded yet.")
        return

    print(f"{'Run ID':<18} {'Timestamp':<25} {'Scenario':<22} {'Harness':<20} {'Recall':<10} {'Verdict'}")
    print("-" * 110)

    for run in history[:args.limit]:
        m = run.metrics
        pass_str = format_status(m.simbian_pass_status)
        print(f"{run.run_id:<18} {run.timestamp[:19]:<25} {run.scenario_id:<22} {run.agent_harness:<20} {m.overall_recall*100:>5.1f}%    {pass_str}")
    print(f"\nShowing up to {args.limit} recent runs.\n")


def cmd_serve(args: argparse.Namespace) -> None:
    """Launch the interactive web dashboard."""
    import uvicorn
    from web.server import create_app

    app = create_app()
    format_header("STARTING CYBER DEFENSE BENCHMARK WEB DASHBOARD")
    print(f"🚀 Web UI serving at: \033[1;32mhttp://{args.host}:{args.port}\033[0m")
    print("Press Ctrl+C to stop.")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


def main() -> None:
    """Main CLI entrypoint parser."""
    parser = argparse.ArgumentParser(
        description="Simbian Cyber Defense Benchmark Evaluation CLI (BenchHub + Harbor + Gemini 3.7 Flash)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # list-scenarios
    subparsers.add_parser("list-scenarios", help="List all available cybersecurity benchmark scenarios")

    # list-slices
    subparsers.add_parser("list-slices", help="List BenchHub dataset slices and filters")

    # list-skills
    subparsers.add_parser("list-skills", help="List registered agent skills and weights from AGENTS.md")

    # run-eval
    eval_parser = subparsers.add_parser("run-eval", help="Execute an evaluation run on a scenario")
    eval_parser.add_argument("--scenario", "-s", default="simbian-apt29-01", help="Scenario ID to evaluate")
    eval_parser.add_argument("--harness", "-H", default="antigravity", choices=["antigravity", "opencode", "baseline"], help="Agent harness")
    eval_parser.add_argument("--model", "-m", default="gemini-3.7-flash", help="Underlying LLM model")
    eval_parser.add_argument("--thinking-budget", "-b", type=int, default=2048, help="Thinking token budget")
    eval_parser.add_argument("--live", action="store_true", help="Invoke live Gemini 3.7 Flash API via GenAI SDK")
    eval_parser.add_argument("--sandbox-mode", default="local-isolated", choices=["local-isolated", "docker", "cloud-sandbox"], help="Harbor sandbox isolation mode")
    eval_parser.add_argument("--slice", help="BenchHub dataset slice ID")
    eval_parser.add_argument("--output", "-o", help="File path to save evaluation report (.md or .json)")

    # compare-harnesses
    comp_parser = subparsers.add_parser("compare-harnesses", help="Run 3-way harness comparison on a scenario")
    comp_parser.add_argument("--scenario", "-s", default="simbian-apt29-01", help="Scenario ID to benchmark")
    comp_parser.add_argument("--model", "-m", default="gemini-3.7-flash", help="Underlying LLM model")
    comp_parser.add_argument("--thinking-budget", "-b", type=int, default=2048, help="Thinking token budget")
    comp_parser.add_argument("--live", action="store_true", help="Invoke live Gemini 3.7 Flash API")

    # history
    hist_parser = subparsers.add_parser("history", help="List recent evaluation runs")
    hist_parser.add_argument("--limit", "-n", type=int, default=15, help="Max runs to display")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Launch interactive Web Dashboard")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Server host binding")
    serve_parser.add_argument("--port", type=int, default=8080, help="Server port")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "list-scenarios": cmd_list_scenarios,
        "list-slices": cmd_list_slices,
        "list-skills": cmd_list_skills,
        "run-eval": cmd_run_eval,
        "compare-harnesses": cmd_compare_harnesses,
        "history": cmd_history,
        "serve": cmd_serve,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
