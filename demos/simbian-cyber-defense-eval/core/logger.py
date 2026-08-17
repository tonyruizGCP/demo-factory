"""Structured JSON Logger for AgentOps Observability."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach custom contextual metadata if provided in extra
        if hasattr(record, "trace_id"):
            log_obj["trace_id"] = record.trace_id
        if hasattr(record, "span_id"):
            log_obj["span_id"] = record.span_id
        if hasattr(record, "agent_role"):
            log_obj["agent_role"] = record.agent_role
        if hasattr(record, "step_index"):
            log_obj["step_index"] = record.step_index
        if hasattr(record, "intent"):
            log_obj["intent"] = record.intent
        if hasattr(record, "outcome"):
            log_obj["outcome"] = record.outcome
        if hasattr(record, "scenario_id"):
            log_obj["scenario_id"] = record.scenario_id

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def get_logger(name: str = "cyber_eval") -> logging.Logger:
    """Get or configure a structured JSON logger.

    Args:
        name: Name of the logger component.

    Returns:
        logging.Logger: Configured logger with JSON output format.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
