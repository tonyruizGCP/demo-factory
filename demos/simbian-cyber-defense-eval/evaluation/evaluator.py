"""Orchestrator for Cyber Defense Benchmark Evaluations.

Connects BenchHub dataset curation, Harbor sandboxed execution,
agent harnesses (Antigravity, Open Code, Baseline), and verifier metrics.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional
import uuid

try:
    from ..benchhub.curator import BenchHubCurator
    from ..core.models import (
        AgentTrajectory,
        EvaluationMetricResult,
        EvalRunSummary,
        ScenarioTask,
    )
    from ..harbor.sandbox import HarborSandbox
    from ..harbor.task_spec import HarborEnvironmentConfig, HarborTaskSpec
    from ..harbor.verifier import HarborVerifier
    from ..harnesses.antigravity_harness import AntigravityAgentHarness
    from ..harnesses.base import BaseAgentHarness
    from ..harnesses.baseline_harness import SingleTurnBaselineHarness
    from ..harnesses.opencode_harness import OpenCodeAgentHarness
except (ImportError, ValueError):
    from benchhub.curator import BenchHubCurator
    from core.models import (
        AgentTrajectory,
        EvaluationMetricResult,
        EvalRunSummary,
        ScenarioTask,
    )
    from harbor.sandbox import HarborSandbox
    from harbor.task_spec import HarborEnvironmentConfig, HarborTaskSpec
    from harbor.verifier import HarborVerifier
    from harnesses.antigravity_harness import AntigravityAgentHarness
    from harnesses.base import BaseAgentHarness
    from harnesses.baseline_harness import SingleTurnBaselineHarness
    from harnesses.opencode_harness import OpenCodeAgentHarness


class CyberDefenseEvaluator:
    """End-to-end evaluation orchestrator for Simbian Cyber Defense Benchmark."""

    def __init__(self, history_file: Optional[Path] = None):
        self.curator = BenchHubCurator()
        self.verifier = HarborVerifier()
        self.history_file = history_file or (Path(__file__).parent.parent / "eval_history.json")
        self._history: List[EvalRunSummary] = []
        self._load_history()

    def _load_history(self) -> None:
        """Load past evaluation run history from JSON file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._history = [EvalRunSummary(**item) for item in data]
            except Exception as e:
                print(f"[Evaluator] Warning loading history: {e}")

    def _save_history(self) -> None:
        """Persist evaluation runs to JSON file."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([item.model_dump() for item in self._history], f, indent=2)
        except Exception as e:
            print(f"[Evaluator] Warning saving history: {e}")

    def get_harness(
        self,
        harness_name: str,
        model_name: str = "gemini-3.7-flash",
        thinking_budget: int = 2048,
    ) -> BaseAgentHarness:
        """Factory method to instantiate the requested agent harness."""
        normalized = harness_name.lower().replace(" ", "").replace("-", "").replace("_", "")
        if "antigravity" in normalized:
            return AntigravityAgentHarness(model_name=model_name, thinking_budget=thinking_budget)
        elif "opencode" in normalized:
            return OpenCodeAgentHarness(model_name=model_name, thinking_budget=thinking_budget)
        elif "baseline" in normalized:
            return SingleTurnBaselineHarness(model_name=model_name, thinking_budget=thinking_budget)
        else:
            return AntigravityAgentHarness(model_name=model_name, thinking_budget=thinking_budget)

    def run_evaluation(
        self,
        scenario_id: str,
        harness_name: str = "antigravity",
        model_name: str = "gemini-3.7-flash",
        thinking_budget: int = 2048,
        use_live_llm: bool = False,
        harbor_sandbox_mode: str = "local-isolated",
        benchhub_slice: str = "all-tactics",
    ) -> EvalRunSummary:
        """Execute a single scenario evaluation run end-to-end."""
        scenario = self.curator.get_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario '{scenario_id}' not found in BenchHub catalog.")

        # 1. Create Harbor Task Specification and Sandbox
        task_spec = HarborTaskSpec(
            task_id=f"harbor-task-{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.id,
            instruction=f"Investigate alert: {scenario.initial_alert}. Identify all MITRE ATT&CK techniques.",
            environment=HarborEnvironmentConfig(sandbox_mode=harbor_sandbox_mode),
        )

        sandbox = HarborSandbox(task_spec=task_spec)
        sandbox.start(events=scenario.events)

        # 2. Instantiate Agent Harness & Run Threat Hunting Investigation
        harness = self.get_harness(
            harness_name=harness_name,
            model_name=model_name,
            thinking_budget=thinking_budget,
        )

        trajectory = harness.run_investigation(
            scenario=scenario,
            sandbox=sandbox,
            use_live_llm=use_live_llm,
        )

        # 3. Terminate Sandbox
        trial_job = sandbox.terminate()

        # 4. Harbor Ground-Truth Verification & Scoring
        metrics = self.verifier.verify_detections(
            scenario=scenario,
            agent_detections=trajectory.detected_threats,
            total_queries=trajectory.total_queries,
            agent_name=harness.name,
            model_name=model_name,
            thinking_budget=thinking_budget,
        )

        # 5. Compile Run Summary
        run_id = f"eval-{uuid.uuid4().hex[:8]}"
        summary = EvalRunSummary(
            run_id=run_id,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            scenario_id=scenario.id,
            scenario_title=scenario.title,
            agent_harness=harness.name,
            model_name=model_name,
            thinking_budget=thinking_budget,
            harbor_sandbox_mode=harbor_sandbox_mode,
            benchhub_slice=benchhub_slice,
            metrics=metrics,
            trajectory=trajectory,
        )

        self._history.insert(0, summary)
        self._save_history()
        return summary

    def list_history(self) -> List[EvalRunSummary]:
        """Return all historical evaluation runs."""
        return self._history

    def get_run(self, run_id: str) -> Optional[EvalRunSummary]:
        """Retrieve a specific past evaluation run by ID."""
        for run in self._history:
            if run.run_id == run_id:
                return run
        return None
