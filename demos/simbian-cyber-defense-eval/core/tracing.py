"""OpenTelemetry and Distributed Tracing Provider for Cyber Defense Evaluations."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional
from core.logger import get_logger

logger = get_logger("tracing")


class TraceSpan:
    """Represents a distributed trace span capturing execution latency, intent, and outcome."""

    def __init__(
        self,
        name: str,
        trace_id: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.trace_id = trace_id
        self.span_id = str(uuid.uuid4())[:8]
        self.parent_span_id = parent_span_id
        self.attributes: Dict[str, Any] = attributes or {}
        self.start_time = time.perf_counter()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
        self.status: str = "RUNNING"
        self.events: List[Dict[str, Any]] = []

    def set_attribute(self, key: str, value: Any) -> None:
        """Set metadata attribute on span."""
        self.attributes[key] = value

    def add_event(self, name: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Record an event within the span."""
        self.events.append({
            "name": name,
            "timestamp": time.perf_counter() - self.start_time,
            "payload": payload or {},
        })

    def end(self, status: str = "OK") -> None:
        """Finish the span execution."""
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to serializable dictionary."""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
        }


class AgentTracer:
    """Manages distributed traces and OpenTelemetry-compatible span trees."""

    def __init__(self, service_name: str = "simbian-cyber-defense-eval"):
        self.service_name = service_name
        self.current_trace_id: str = str(uuid.uuid4())[:16]
        self.active_spans: List[TraceSpan] = []
        self.completed_spans: List[TraceSpan] = []

    def start_trace(self, scenario_id: str) -> str:
        """Initialize a new trace context for an evaluation run.

        Args:
            scenario_id: The ID of the scenario being evaluated.

        Returns:
            str: The generated 16-character trace ID.
        """
        self.current_trace_id = str(uuid.uuid4())[:16]
        self.completed_spans = []
        return self.current_trace_id

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Generator[TraceSpan, None, None]:
        """Context manager to wrap execution blocks in a trace span.

        Args:
            name: Span operation name (e.g. 'sql_telemetry_query', 'llm_inference').
            attributes: Initial span attributes.

        Yields:
            TraceSpan: The active span instance.
        """
        parent_span_id = self.active_spans[-1].span_id if self.active_spans else None
        span = TraceSpan(
            name=name,
            trace_id=self.current_trace_id,
            parent_span_id=parent_span_id,
            attributes=attributes,
        )
        self.active_spans.append(span)

        try:
            yield span
            span.end(status="OK")
        except Exception as e:
            span.set_attribute("error", str(e))
            span.end(status="ERROR")
            raise
        finally:
            self.active_spans.pop()
            self.completed_spans.append(span)

    def get_trace_summary(self) -> Dict[str, Any]:
        """Return exportable trace summary of all completed spans."""
        return {
            "service_name": self.service_name,
            "trace_id": self.current_trace_id,
            "total_spans": len(self.completed_spans),
            "spans": [s.to_dict() for s in self.completed_spans],
        }


# Global singleton tracer
tracer = AgentTracer()
