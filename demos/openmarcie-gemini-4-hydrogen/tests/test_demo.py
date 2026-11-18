"""Pytest suite for OpenMARCIE Vol10 × Gemini 4 Hydrogen Demo."""

import os
from pathlib import Path
from fastapi.testclient import TestClient

os.environ["DEMO_SIMULATION"] = "1"

from app.agent import AssemblyTimeline, app as agent_app, root_agent
from app.main import web_app

client = TestClient(web_app)


def test_agent_entrypoint_naming():
    assert root_agent is agent_app
    assert root_agent["model"] == "gemini-4-hydrogen"


def test_no_google_cloud_project_in_app():
    app_dir = Path(__file__).resolve().parent.parent / "app"
    for py_file in app_dir.glob("*.py"):
        assert "GOOGLE_CLOUD_PROJECT" not in py_file.read_text(), f"Forbidden env var in {py_file}"


def test_health_and_media():
    h = client.get("/api/health")
    assert h.status_code == 200
    data = h.json()
    assert data["status"] == "ok"
    assert data["model"] == "gemini-4-hydrogen"
    assert data["clip_ready"] is True

    m = client.get("/api/media")
    assert m.status_code == 200
    assert len(m.json()["keyframes"]) == 3


def test_analyze_all_modes_simulated():
    r1 = client.post("/api/analyze", json={"mode": "temporal_actions", "thinking_level": "MEDIUM"})
    assert r1.status_code == 200
    timeline = AssemblyTimeline.model_validate(r1.json()["result"])
    assert timeline.total_segments >= 1

    for mode in ("spatial_transitions", "ehs_audit"):
        r = client.post("/api/analyze", json={"mode": mode, "thinking_level": "HIGH"})
        assert r.status_code == 200
        assert isinstance(r.json()["result"], str)
        assert len(r.json()["result"]) > 40
