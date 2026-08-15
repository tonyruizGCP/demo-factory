"""Markdown and JSON Evaluation Report Generator for Cyber Defense Benchmarks."""

from __future__ import annotations

import json
try:
    from ..core.mitre import get_tactic_metadata
    from ..core.models import EvalRunSummary
except (ImportError, ValueError):
    from core.mitre import get_tactic_metadata
    from core.models import EvalRunSummary


class ReportGenerator:
    """Generates detailed Markdown and JSON summary reports from evaluation runs."""

    @staticmethod
    def generate_markdown_report(summary: EvalRunSummary) -> str:
        """Generate a GitHub-flavored markdown report."""
        m = summary.metrics
        t = summary.trajectory

        status_badge = "🟢 **PASSED SIMBIAN BENCHMARK**" if m.simbian_pass_status else "🔴 **FAILED SIMBIAN BENCHMARK**"

        md = []
        md.append(f"# 🛡️ Cyber Defense Benchmark Evaluation Report: {summary.scenario_title}")
        md.append(f"**Run ID**: `{summary.run_id}` | **Timestamp**: `{summary.timestamp}`\n")
        md.append(f"### Evaluation Verdict: {status_badge}")
        md.append(f"> **Summary**: {m.summary_verdict}\n")

        md.append("## ⚙️ Configuration")
        md.append(f"- **Agent Harness**: `{summary.agent_harness}`")
        md.append(f"- **Model**: `{summary.model_name}`")
        md.append(f"- **Thinking Budget**: `{summary.thinking_budget}` tokens")
        md.append(f"- **Harbor Sandbox Mode**: `{summary.harbor_sandbox_mode}`")
        md.append(f"- **BenchHub Slice**: `{summary.benchhub_slice}`\n")

        md.append("## 📊 Benchmark Performance Summary")
        md.append("| Metric | Score | Benchmark Target | Status |")
        md.append("| :--- | :--- | :--- | :--- |")
        md.append(f"| **Overall Recall** | **{m.overall_recall * 100:.1f}%** | $\\ge$ 50.0% per tactic | {'✅ Pass' if m.overall_recall >= 0.5 else '⚠️ Needs Tuning'} |")
        md.append(f"| **Overall Precision** | **{m.overall_precision * 100:.1f}%** | High Precision | {'✅ Pass' if m.overall_precision >= 0.8 else '⚠️ High False Positives'} |")
        md.append(f"| **Overall F1 Score** | **{m.overall_f1 * 100:.1f}%** | Balanced F1 | - |")
        md.append(f"| **MITRE Chain Coverage** | **{m.mitre_chain_coverage * 100:.1f}%** | 100% Chain | {'✅ Full' if m.mitre_chain_coverage == 1.0 else '⚠️ Partial'} |")
        md.append(f"| **Query Efficiency** | **{m.query_efficiency_score}** dets/query | Efficient Hunt | - |")
        md.append(f"| **False Discovery Rate** | **{m.false_discovery_rate * 100:.1f}%** | $\\le$ 15.0% | {'✅ Low FP' if m.false_discovery_rate <= 0.15 else '⚠️ Elevated FP'} |\n")

        md.append("## 🎯 MITRE ATT&CK 12-Tactic Breakdown")
        md.append("| Tactic | Ground Truth | True Positives | False Positives | Recall | Precision | Simbian Pass ($\\ge 50\\%$) |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

        for tactic_val, score in m.tactic_scores.items():
            meta = get_tactic_metadata(score.tactic)
            icon = meta.get("icon", "🛡️")
            name = meta.get("name", tactic_val)
            pass_str = "✅ Pass" if score.passed_simbian_bar else "❌ Fail"
            md.append(f"| {icon} **{name}** | {score.ground_truth_count} | {score.true_positives} | {score.false_positives} | {score.recall * 100:.1f}% | {score.precision * 100:.1f}% | {pass_str} |")

        md.append("\n## 🔍 Agent Forensic Detections")
        if t.detected_threats:
            for idx, det in enumerate(t.detected_threats, 1):
                verdict_icon = "✅ [TRUE POSITIVE]" if det.is_true_positive else "❌ [FALSE POSITIVE]"
                md.append(f"### Detection #{idx}: {det.technique_name} (`{det.technique_id}`) - {verdict_icon}")
                md.append(f"- **Tactic**: `{det.tactic.value}`")
                md.append(f"- **Confidence**: `{det.confidence * 100:.0f}%`")
                md.append(f"- **Explanation**: {det.explanation}")
                if det.evidence_event_ids:
                    md.append(f"- **Evidence Event IDs**: `{det.evidence_event_ids}`")
                if det.matched_ground_truth_rule:
                    md.append(f"- **Matched Ground Truth Rule**: `{det.matched_ground_truth_rule}`")
                md.append("")
        else:
            md.append("_No threats detected by agent._\n")

        md.append("## 🧭 Investigation Trajectory Trace")
        md.append(f"**Total Steps**: `{t.total_steps}` | **Total SQL Queries**: `{t.total_queries}` | **Total Wall-Clock Time**: `{t.execution_time_seconds:.2f}s`\n")

        for step in t.steps:
            md.append(f"#### Step {step.step_index}: {step.agent_role} ({step.duration_ms}ms)")
            if step.thought:
                md.append(f"> **Gemini 3.7 Flash Thought**:\n> {step.thought.replace(chr(10), chr(10) + '> ')}")
            if step.sql_query:
                md.append(f"```sql\n{step.sql_query}\n```")
            if step.tool_output:
                md.append(f"```\n{step.tool_output}\n```")
            md.append("")

        return "\n".join(md)

    @staticmethod
    def generate_json_report(summary: EvalRunSummary) -> str:
        """Generate formatted JSON report."""
        return json.dumps(summary.model_dump(), indent=2)
