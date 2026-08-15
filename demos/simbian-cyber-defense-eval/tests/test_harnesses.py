"""Unit tests for threat hunting agent harnesses."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from benchhub.curator import BenchHubCurator
from harbor.sandbox import HarborSandbox
from harbor.task_spec import HarborEnvironmentConfig, HarborTaskSpec
from harnesses.antigravity_harness import AntigravityAgentHarness
from harnesses.opencode_harness import OpenCodeAgentHarness
from harnesses.baseline_harness import SingleTurnBaselineHarness


def test_antigravity_harness_run():
    curator = BenchHubCurator()
    scenario = curator.get_scenario("simbian-apt29-01")
    assert scenario is not None

    task_spec = HarborTaskSpec(
        task_id="test-antigravity",
        scenario_id=scenario.id,
        instruction="Investigate scenario",
        environment=HarborEnvironmentConfig(sandbox_mode="local-isolated"),
    )
    sandbox = HarborSandbox(task_spec=task_spec)
    sandbox.start(scenario.events)

    harness = AntigravityAgentHarness(model_name="gemini-3.7-flash", thinking_budget=2048)
    trajectory = harness.run_investigation(scenario=scenario, sandbox=sandbox, use_live_llm=False)

    assert trajectory.total_steps >= 3
    assert trajectory.total_queries >= 2
    assert len(trajectory.detected_threats) >= 5
    sandbox.terminate()


def test_opencode_harness_run():
    curator = BenchHubCurator()
    scenario = curator.get_scenario("simbian-apt29-01")
    assert scenario is not None

    task_spec = HarborTaskSpec(
        task_id="test-opencode",
        scenario_id=scenario.id,
        instruction="Investigate scenario",
        environment=HarborEnvironmentConfig(sandbox_mode="local-isolated"),
    )
    sandbox = HarborSandbox(task_spec=task_spec)
    sandbox.start(scenario.events)

    harness = OpenCodeAgentHarness(model_name="gemini-3.7-flash", thinking_budget=2048)
    trajectory = harness.run_investigation(scenario=scenario, sandbox=sandbox, use_live_llm=False)

    assert trajectory.total_steps >= 2
    assert len(trajectory.detected_threats) > 0
    sandbox.terminate()


def test_baseline_harness_run():
    curator = BenchHubCurator()
    scenario = curator.get_scenario("simbian-apt29-01")
    assert scenario is not None

    task_spec = HarborTaskSpec(
        task_id="test-baseline",
        scenario_id=scenario.id,
        instruction="Investigate scenario",
        environment=HarborEnvironmentConfig(sandbox_mode="local-isolated"),
    )
    sandbox = HarborSandbox(task_spec=task_spec)
    sandbox.start(scenario.events)

    harness = SingleTurnBaselineHarness(model_name="gemini-3.7-flash", thinking_budget=0)
    trajectory = harness.run_investigation(scenario=scenario, sandbox=sandbox, use_live_llm=False)

    assert trajectory.total_steps == 1
    assert trajectory.total_queries == 0
    sandbox.terminate()
