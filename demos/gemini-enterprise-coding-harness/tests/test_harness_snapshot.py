"""Unit tests for Harness State & Snapshot Registry."""
import os
import shutil
import tempfile
import pytest

from app.services.harness_snapshot import HarnessSnapshotManager, HarnessSnapshot


@pytest.fixture
def temp_workspace():
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_capture_and_load_snapshot(temp_workspace):
    manager = HarnessSnapshotManager(workspace_root=temp_workspace)
    
    # 1. Capture baseline snapshot
    baseline = manager.capture_snapshot(
        name="baseline_v1",
        evaluation_metrics={"pass_rate": 0.375, "avg_tokens": 3840},
        metadata={"author": "tonyruiz", "version": "1.0.0"},
    )
    assert baseline.name == "baseline_v1"
    assert baseline.evaluation_metrics["pass_rate"] == 0.375
    assert len(baseline.active_tools) >= 5
    assert baseline.code_hash is not None

    # 2. Load snapshot back
    loaded = manager.load_snapshot("baseline_v1")
    assert loaded is not None
    assert loaded.snapshot_id == baseline.snapshot_id
    assert loaded.evaluation_metrics["avg_tokens"] == 3840


def test_diff_snapshots(temp_workspace):
    manager = HarnessSnapshotManager(workspace_root=temp_workspace)

    # Capture baseline
    manager.capture_snapshot(
        name="baseline_v1",
        evaluation_metrics={"pass_rate": 0.375},
        custom_prompts={"system_prompt": "Original prompt v1"},
    )

    # Capture candidate
    manager.capture_snapshot(
        name="candidate_v2",
        evaluation_metrics={"pass_rate": 0.875},
        custom_prompts={"system_prompt": "Tuned prompt with AST guard v2"},
    )

    # Diff
    diff = manager.diff_snapshots("baseline_v1", "candidate_v2")
    assert "system_prompt" in diff["prompt_changes"]
    assert diff["prompt_changes"]["system_prompt"]["before"] == "Original prompt v1"
    assert diff["prompt_changes"]["system_prompt"]["after"] == "Tuned prompt with AST guard v2"
    assert diff["metric_delta"]["pass_rate"]["baseline"] == 0.375
    assert diff["metric_delta"]["pass_rate"]["candidate"] == 0.875


def test_list_snapshots(temp_workspace):
    manager = HarnessSnapshotManager(workspace_root=temp_workspace)
    manager.capture_snapshot("snap1", evaluation_metrics={"pass_rate": 0.5})
    manager.capture_snapshot("snap2", evaluation_metrics={"pass_rate": 0.8})

    snapshots = manager.list_snapshots()
    names = [s["name"] for s in snapshots]
    assert "snap1" in names
    assert "snap2" in names
