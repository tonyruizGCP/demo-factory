"""Trial telemetry, token spend, and trace span schemas."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TokenSpend(BaseModel):
    """Token consumption accounting for an agent trial."""

    model_config = ConfigDict(extra="allow")

    prompt_tokens: int = Field(default=0, ge=0, description="Tokens used in prompt")
    completion_tokens: int = Field(default=0, ge=0, description="Tokens generated in completion")
    total_tokens: int = Field(default=0, ge=0, description="Aggregate token consumption")

    @model_validator(mode="before")
    @classmethod
    def calculate_total(cls, values: Any) -> Any:
        if isinstance(values, dict):
            p = values.get("prompt_tokens", 0) or 0
            c = values.get("completion_tokens", 0) or 0
            t = values.get("total_tokens")
            if t is None:
                values["total_tokens"] = p + c
            elif t == 0 and (p > 0 or c > 0):
                values["total_tokens"] = p + c
        return values


class TraceSpan(BaseModel):
    """Structured execution trace span capturing execution sub-phases."""

    model_config = ConfigDict(extra="allow")

    span_id: str = Field(
        default_factory=lambda: f"span_{uuid.uuid4().hex[:8]}",
        description="Unique trace span identifier",
    )
    name: str = Field(default="execution", description="Span operation name")
    start_time: float = Field(default=0.0, description="Span start timestamp")
    end_time: float = Field(default=0.0, description="Span end timestamp")
    duration_ms: float = Field(default=0.0, description="Span duration in milliseconds")
    status: str = Field(default="OK", description="Span status (e.g. OK, ERROR)")
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual metadata and execution tags",
    )

    @model_validator(mode="before")
    @classmethod
    def sync_duration_and_times(cls, values: Any) -> Any:
        if isinstance(values, dict):
            start = values.get("start_time", 0.0) or 0.0
            end = values.get("end_time", 0.0) or 0.0
            dur = values.get("duration_ms", 0.0) or 0.0

            if dur > 0.0 and end <= start:
                values["end_time"] = start + (dur / 1000.0)
            elif end > start and dur == 0.0:
                values["duration_ms"] = (end - start) * 1000.0
        return values


class TrialTelemetry(BaseModel):
    """Comprehensive telemetry record produced by an evaluation trial."""

    model_config = ConfigDict(extra="allow")

    trial_id: str = Field(
        default_factory=lambda: f"trial_{uuid.uuid4().hex[:8]}",
        description="Unique identifier for the evaluation trial",
    )
    task_id: str = Field(..., description="Target benchmark task identifier")
    candidate_id: str = Field(..., description="Evaluated candidate agent identifier")
    passed: bool = Field(..., description="Binary outcome of verification check")
    exit_code: int = Field(default=0, description="Process exit code from verification")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Trial elapsed time in milliseconds")
    token_spend: TokenSpend = Field(
        default_factory=TokenSpend,
        description="Token accounting breakdown",
    )
    trace_logs: List[Any] = Field(
        default_factory=list,
        description="Execution trace spans and logs",
    )
    raw_error_message: Optional[str] = Field(
        default=None,
        description="Diagnostic error string or stack trace on failure",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task, candidate, or environment metadata propagated to telemetry",
    )

    @model_validator(mode="before")
    @classmethod
    def sanitize_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if values.get("metadata") is None:
                values["metadata"] = {}
            if values.get("trace_logs") is None:
                values["trace_logs"] = []
            if values.get("token_spend") is None:
                values["token_spend"] = TokenSpend()
        return values
