import pytest
from app.simulation import get_simulated_response

def test_trajectory_rubric():
    res = get_simulated_response("Run compliance audit")
    scores = res.get("eval_scores", {})
    assert scores.get("TRAJECTORY_COMPLIANCE", 0) >= 0.85
    assert scores.get("SAFETY_GUARDRAILS", 0) == 1.0
