"""Strategic Multi-Model Routing Engine for Cyber Defense Agents."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional
from core.logger import get_logger

logger = get_logger("model_router")


class TaskComplexity(str, Enum):
    """Complexity tiers for strategic LLM task routing."""
    FAST_TRIAGE = "fast_triage"          # Quick SQL generation, regex filtering
    DEEP_REASONING = "deep_reasoning"    # Kill-chain correlation, parentage tracing
    CRITICAL_SYNTHESIS = "synthesis"     # Final MITRE ATT&CK extraction & report authoring


class ModelRouter:
    """Routes specific threat hunting tasks to the optimal Gemini model tier."""

    DEFAULT_ROUTING_MAP = {
        TaskComplexity.FAST_TRIAGE: {
            "model_name": "gemini-2.5-flash",
            "thinking_budget": 1024,
            "description": "High-throughput, low-latency SQL query generation and event filtering.",
        },
        TaskComplexity.DEEP_REASONING: {
            "model_name": "gemini-3.7-flash",
            "thinking_budget": 2048,
            "description": "Extended thinking model for complex multi-stage telemetry correlation.",
        },
        TaskComplexity.CRITICAL_SYNTHESIS: {
            "model_name": "gemini-2.5-pro",
            "thinking_budget": 4096,
            "description": "High-capacity frontier reasoning model for definitive MITRE ATT&CK synthesis.",
        },
    }

    def __init__(self, overrides: Optional[Dict[TaskComplexity, Dict[str, Any]]] = None):
        self.routing_map = self.DEFAULT_ROUTING_MAP.copy()
        if overrides:
            self.routing_map.update(overrides)

    def route(self, task_type: TaskComplexity, requested_model: Optional[str] = None) -> Dict[str, Any]:
        """Determine optimal model and thinking budget for a given agent task.

        Args:
            task_type: The functional complexity tier of the task.
            requested_model: Optional explicit model override from user CLI or API.

        Returns:
            Dict[str, Any]: Routing decision containing model_name, thinking_budget, and rationale.
        """
        route_config = self.routing_map.get(task_type, self.routing_map[TaskComplexity.DEEP_REASONING])
        selected_model = requested_model if requested_model and requested_model != "auto" else route_config["model_name"]

        decision = {
            "task_type": task_type.value,
            "model_name": selected_model,
            "thinking_budget": route_config["thinking_budget"],
            "rationale": route_config["description"],
        }

        logger.info(
            f"Strategic Model Route: Task '{task_type.value}' -> {selected_model} (Budget: {route_config['thinking_budget']})",
            extra={"task_type": task_type.value, "selected_model": selected_model}
        )
        return decision
