import pytest
from app.simulation import get_simulated_drive_response

def test_eval_scores_threshold():
    res = get_simulated_drive_response("Test query", "1AbCdEfGhIjKlMnOpQrStUvWxYz_12345")
    scores = res.get("eval_scores", {})
    
    assert scores.get("FINAL_RESPONSE_QUALITY", 0) >= 0.85
    assert scores.get("TRAJECTORY_COMPLIANCE", 0) >= 0.85
    assert scores.get("SAFETY_GUARDRAILS", 0) == 1.0
