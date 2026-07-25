import pytest
from app.agent import root_agent

def test_auto_resolve_routing():
    alert = {"alert_id": "ALT-100", "severity": "WARNING", "service_name": "auth-service"}
    res = root_agent.triage_alert(alert)
    assert res["status"] == "AUTO_RESOLVED"
    assert res["node"] == "auto_resolve_node"

def test_investigate_routing():
    alert = {"alert_id": "ALT-900", "severity": "CRITICAL", "service_name": "checkout-payment-service", "error_message": "Pool timeout"}
    res = root_agent.triage_alert(alert)
    assert res["status"] == "INVESTIGATED"
    assert res["node"] == "investigate_node"
    assert "# 🚨 SRE Incident Report" in res["report_markdown"]
