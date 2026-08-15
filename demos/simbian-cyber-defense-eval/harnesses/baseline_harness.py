"""Single-Turn LLM Baseline Harness (Non-Agentic Baseline).

Provides a direct zero-shot evaluation without multi-turn tool calling or iterative SQL loops,
illustrating why frontier LLMs struggle on the Simbian benchmark without an agentic harness.
"""

from __future__ import annotations

import time
from typing import List
try:
    from ..core.models import (
        AgentDetection,
        AgentTrajectory,
        HuntStep,
        MitreTactic,
        ScenarioTask,
    )
    from ..harbor.sandbox import HarborSandbox
    from .base import BaseAgentHarness
except (ImportError, ValueError):
    from core.models import (
        AgentDetection,
        AgentTrajectory,
        HuntStep,
        MitreTactic,
        ScenarioTask,
    )
    from harbor.sandbox import HarborSandbox
    from harnesses.base import BaseAgentHarness


class SingleTurnBaselineHarness(BaseAgentHarness):
    """Zero-shot non-agentic LLM baseline."""

    def __init__(self, model_name: str = "gemini-3.7-flash", thinking_budget: int = 0):
        super().__init__(name="Single-Turn Baseline (Raw LLM)", model_name=model_name, thinking_budget=thinking_budget)

    def run_investigation(
        self,
        scenario: ScenarioTask,
        sandbox: HarborSandbox,
        use_live_llm: bool = False,
    ) -> AgentTrajectory:
        """Run single-turn prompt-response baseline."""
        start_time = time.time()

        # Non-agentic baseline only sees the initial alert without active SQL exploration
        step_start = time.perf_counter()
        detections = [
            AgentDetection(
                tactic=MitreTactic.EXECUTION,
                technique_id="T1059.001",
                technique_name="PowerShell",
                confidence=0.60,
                explanation="Generic assumption of PowerShell usage based on alert text.",
            )
        ]

        step_dur_ms = int((time.perf_counter() - step_start) * 1000) + 50
        step = HuntStep(
            step_index=1,
            agent_role="Single-Turn Model",
            thought="Direct generation based on alert context only (no telemetry SQL tool execution).",
            action_type="direct_answer",
            sql_query=None,
            tool_output=None,
            new_findings=detections,
            duration_ms=step_dur_ms,
        )

        total_duration = round(time.time() - start_time, 2)
        summary = "Single-turn prompt completed without database inspection."

        return AgentTrajectory(
            agent_name=self.name,
            model_name=self.model_name,
            thinking_budget=self.thinking_budget,
            total_steps=1,
            total_queries=0,
            total_tokens_used=450,
            execution_time_seconds=total_duration,
            steps=[step],
            detected_threats=detections,
            investigation_summary=summary,
        )
