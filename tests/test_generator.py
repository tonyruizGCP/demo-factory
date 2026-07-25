import os
import pytest
from app.models import GenerateDemoRequest
from app.generator import DemoGeneratorEngine

def test_generate_project_scaffolding(tmp_path):
    engine = DemoGeneratorEngine()
    req = GenerateDemoRequest(
        customer_use_case="Test Healthcare Triage Assistant",
        tech_approach="ADK 2.0 + FastAPI + Vertex AI",
        rigor_level="agentic_engineering",
        project_slug="test-healthcare-triage"
    )
    
    res = engine.generate_project(req)
    
    assert res.status == "SUCCESS"
    assert res.project_name == "test-healthcare-triage"
    assert os.path.exists(os.path.join(res.project_path, "AGENTS.md"))
    assert os.path.exists(os.path.join(res.project_path, ".github", "workflows", "ci.yml"))
    assert os.path.exists(os.path.join(res.project_path, "app", "agent.py"))
    assert os.path.exists(os.path.join(res.project_path, "app", "simulation.py"))
    assert os.path.exists(os.path.join(res.project_path, "tests", "test_agent.py"))
    assert "pyopenssl==24.3.0" in res.agents_md_content
