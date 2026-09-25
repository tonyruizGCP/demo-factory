"""Unit and integration tests for the Gemini Enterprise Coding Harness adapter."""
import sys
from pathlib import Path
import pytest

from harness_optimizer.benchhub.schema import ATIFTask, DifficultyLevel, BehavioralTag, VerificationSpec
from harness_optimizer.harbor.gemini_enterprise_adapter import (
    GeminiEnterpriseCodingAdapter,
    _ensure_gemini_harness_importable,
)
from harness_optimizer.harbor.telemetry import TrialTelemetry
from harness_optimizer.synthetic.gemini_enterprise_tasks import (
    generate_enterprise_benchmark_suite,
    get_enterprise_coding_tasks,
)


def test_gemini_enterprise_import_and_instantiation():
    """Verify adapter locates gemini-enterprise-coding-harness and initializes."""
    harness_path = _ensure_gemini_harness_importable()
    assert harness_path.exists()

    adapter = GeminiEnterpriseCodingAdapter(candidate_config={"candidate_id": "test_init"})
    assert adapter.candidate_id == "test_init"
    assert adapter.orchestrator is not None


def test_gemini_enterprise_execute_task_returns_telemetry():
    """Verify executing an ATIF task returns valid TrialTelemetry with spans and tokens."""
    adapter = GeminiEnterpriseCodingAdapter()
    task = ATIFTask(
        task_id="test_ge_01",
        instruction="Refactor session manager with async methods",
        difficulty=DifficultyLevel.HARD,
        behavioral_tags=[BehavioralTag.TOOL_SELECTION, BehavioralTag.STATE_MUTATION],
        verification=VerificationSpec(command="pytest -q", timeout_seconds=10),
    )

    telemetry = adapter.execute_trial(task)
    assert isinstance(telemetry, TrialTelemetry)
    assert telemetry.task_id == "test_ge_01"
    assert telemetry.latency_ms > 0.0
    assert telemetry.token_spend.total_tokens > 0
    assert len(telemetry.trace_logs) >= 3
    # Check that prewalk and subagent spans were captured
    span_types = {span.span_type for span in telemetry.trace_logs}
    assert "prewalk_grounding" in span_types or "tool_invocation" in span_types


def test_gemini_enterprise_simulated_failure_telemetry():
    """Verify candidate with formatting failure returns passed=False and raw error message."""
    adapter = GeminiEnterpriseCodingAdapter(candidate_config={"simulate_failure": True})
    task = ATIFTask(
        task_id="test_ge_fail",
        instruction="Enforce strict formatting",
        difficulty=DifficultyLevel.EASY,
        behavioral_tags=[BehavioralTag.CONSTRAINT_ADHERENCE],
        verification=VerificationSpec(command="echo ok", timeout_seconds=10),
    )

    telemetry = adapter.execute_trial(task)
    assert telemetry.passed is False
    assert telemetry.exit_code != 0
    assert telemetry.raw_error_message is not None
    assert "ToolFormattingError" in telemetry.raw_error_message


def test_enterprise_benchmark_suite_generation():
    """Verify procedural enterprise benchmark suite produces valid ATIF tasks."""
    suite = generate_enterprise_benchmark_suite(num_tasks=12)
    assert len(suite.tasks) == 12
    assert suite.metadata.get("target_harness") == "gemini-enterprise-coding-harness"
    for t in suite.tasks:
        assert isinstance(t, ATIFTask)
        assert len(t.behavioral_tags) > 0
