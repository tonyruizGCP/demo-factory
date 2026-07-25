import pytest
from app.eval_runner import execute_eval_suite
from app.simulation import calculate_tco, TCOCalculationRequest

def test_eval_suite_execution():
    res = execute_eval_suite("ecommerce")
    assert res.overall_passed is True
    assert res.deterministic_score == 1.0
    assert res.trajectory_score >= 0.85

def test_tco_calculation():
    req = TCOCalculationRequest(features_count=10, queries_per_day=500, average_context_tokens=15000)
    res = calculate_tco(req)
    assert res.vibe_coding_total_annual > res.agentic_total_annual
    assert res.token_burn_reduction_pct > 50.0
    assert res.crossover_months > 0
