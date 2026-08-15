"""Unit and integration tests for CyberDefenseEvaluator."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.evaluator import CyberDefenseEvaluator


def test_evaluator_end_to_end_antigravity():
    evaluator = CyberDefenseEvaluator()
    summary = evaluator.run_evaluation(
        scenario_id="simbian-apt29-01",
        harness_name="antigravity",
        model_name="gemini-3.7-flash",
        thinking_budget=2048,
        use_live_llm=False,
    )
    
    assert summary.metrics.simbian_pass_status is True
    assert summary.metrics.overall_recall == 1.0
    assert summary.metrics.overall_precision > 0.90
    assert summary.trajectory.total_queries >= 3


def test_evaluator_end_to_end_opencode():
    evaluator = CyberDefenseEvaluator()
    summary = evaluator.run_evaluation(
        scenario_id="simbian-apt29-01",
        harness_name="opencode",
        model_name="gemini-3.7-flash",
        thinking_budget=2048,
        use_live_llm=False,
    )
    
    assert summary.metrics.overall_recall > 0.0
    assert summary.trajectory.total_steps >= 2


def test_evaluator_end_to_end_baseline():
    evaluator = CyberDefenseEvaluator()
    summary = evaluator.run_evaluation(
        scenario_id="simbian-apt29-01",
        harness_name="baseline",
        model_name="gemini-3.7-flash",
        thinking_budget=0,
        use_live_llm=False,
    )
    
    assert summary.metrics.overall_recall < 0.50
    assert summary.metrics.simbian_pass_status is False
