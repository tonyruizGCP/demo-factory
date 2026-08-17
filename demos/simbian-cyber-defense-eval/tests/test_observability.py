"""Unit tests for Observability, Tracing, and PII Redaction modules."""

import json
import logging
from core.logger import JSONFormatter, get_logger
from core.pii_scrubber import PIIScrubber
from core.tracing import AgentTracer, TraceSpan, tracer


def test_pii_scrubber_redaction():
    raw_text = "Alert: Admin user john.doe@enterprise.com used API key AIzaSyA1234567890abcdef1234567890abc with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9. Token password=SuperSecretPassword123!"
    sanitized = PIIScrubber.redact_text(raw_text)

    assert "[REDACTED_EMAIL]" in sanitized
    assert "john.doe@enterprise.com" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "AIzaSyA1234567890abcdef1234567890abc" not in sanitized
    assert "[REDACTED_TOKEN]" in sanitized
    assert "[REDACTED_SECRET]" in sanitized


def test_pii_scrubber_nested_object():
    payload = {
        "user_email": "analyst@acme.corp",
        "nested": {
            "api_key": "AIzaSyA9876543210fedcba9876543210fed",
            "notes": "Legitimate admin activity",
        },
        "tags": ["token: Bearer abcdef1234567890abcdef1234567890"],
    }
    clean = PIIScrubber.sanitize_object(payload)
    assert clean["user_email"] == "[REDACTED_EMAIL]"
    assert clean["nested"]["api_key"] == "[REDACTED_API_KEY]"


def test_structured_json_logger():
    logger = get_logger("test_obs")
    record = logging.LogRecord(
        name="test_obs",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Executing threat hunt query",
        args=(),
        exc_info=None,
    )
    record.trace_id = "trace-12345"
    record.agent_role = "Lead Threat Hunter"
    record.intent = "Inspect Sysmon Event ID 1"

    formatter = JSONFormatter()
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["trace_id"] == "trace-12345"
    assert parsed["agent_role"] == "Lead Threat Hunter"
    assert parsed["intent"] == "Inspect Sysmon Event ID 1"


def test_opentelemetry_tracing():
    custom_tracer = AgentTracer("test_service")
    trace_id = custom_tracer.start_trace("simbian-apt29-01")
    assert len(trace_id) == 16

    with custom_tracer.start_span("root_eval", attributes={"scenario": "apt29"}) as root_span:
        assert root_span.status == "RUNNING"
        with custom_tracer.start_span("child_query", attributes={"sql": "SELECT 1"}) as child_span:
            child_span.add_event("query_executed", {"rows": 5})
            assert child_span.parent_span_id == root_span.span_id

    summary = custom_tracer.get_trace_summary()
    assert summary["total_spans"] == 2
    assert summary["spans"][0]["status"] == "OK"
    assert summary["spans"][1]["status"] == "OK"
