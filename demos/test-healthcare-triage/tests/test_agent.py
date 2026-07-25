import pytest
from app.agent import root_agent
from app.simulation import get_simulated_response

def test_root_agent_export():
    assert root_agent is not None
    assert root_agent.name == "test-healthcare-triage-agent"

def test_simulation_fallback():
    res = get_simulated_response("Test query")
    assert "Processed request" in res["agent_response"]
    assert res["eval_scores"]["FINAL_RESPONSE_QUALITY"] >= 0.80
