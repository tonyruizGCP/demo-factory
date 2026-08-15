"""Unit tests for Harbor sandbox isolation and SQL execution."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from harbor.sandbox import HarborSandbox
from harbor.task_spec import HarborEnvironmentConfig, HarborTaskSpec
from core.models import LogEvent


def test_harbor_sandbox_sql_execution():
    task_spec = HarborTaskSpec(
        task_id="test-task-1",
        scenario_id="simbian-apt29-01",
        instruction="Test SQL query execution in sandbox",
        environment=HarborEnvironmentConfig(sandbox_mode="local-isolated"),
    )
    sandbox = HarborSandbox(task_spec=task_spec)

    sample_events = [
        LogEvent(
            id=1,
            timestamp="2026-08-14T10:00:00Z",
            event_id=1,
            source="Sysmon",
            host="WKSTN-01",
            user="alice",
            process_name="powershell.exe",
            command_line="powershell.exe -enc AAAA...",
            is_malicious=True,
        ),
        LogEvent(
            id=2,
            timestamp="2026-08-14T10:05:00Z",
            event_id=1,
            source="Sysmon",
            host="WKSTN-01",
            user="alice",
            process_name="notepad.exe",
            command_line="notepad.exe test.txt",
            is_malicious=False,
        ),
    ]

    sandbox.start(sample_events)

    # Test read query
    cols, rows, dur, err = sandbox.execute_sql("SELECT id, user, process_name FROM events WHERE process_name = 'powershell.exe';")
    assert err is None
    assert len(rows) == 1
    assert rows[0][2] == "powershell.exe"

    # Test security restriction (DROP TABLE forbidden)
    cols, rows, dur, err = sandbox.execute_sql("DROP TABLE events;")
    assert err is not None
    assert "Security Violation" in err

    trial = sandbox.terminate()
    assert trial.status == "COMPLETED"
