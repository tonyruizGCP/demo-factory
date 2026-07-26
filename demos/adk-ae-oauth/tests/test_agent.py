import pytest
from unittest.mock import MagicMock
from app.agent import root_agent
from app.simulation import get_simulated_drive_response
from app.tools import negotiate_creds

def test_root_agent_export():
    assert root_agent is not None

def test_simulation_drive_retrieval():
    res = get_simulated_drive_response("Read file 1AbCdEfGhIjKlMnOpQrStUvWxYz_12345", "1AbCdEfGhIjKlMnOpQrStUvWxYz_12345")
    assert res["status"] == "success"
    assert "Q3_Strategic_AI_Architecture.gdoc" in res["file_name"]
    assert "Stage 1" in res["oauth_stage"]

def test_negotiate_creds_stage_1_injected():
    # Test Stage 1: Injected bearer token in tool_context state
    ctx = MagicMock()
    ctx.state = {"google-drive-auth": "simulated_bearer_token_xyz"}
    creds = negotiate_creds(ctx)
    assert not isinstance(creds, dict)
    assert creds.token == "simulated_bearer_token_xyz"
