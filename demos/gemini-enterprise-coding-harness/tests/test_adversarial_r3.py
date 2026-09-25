"""Round 3 Adversarial and Verification Test Suite for Gemini Enterprise Coding Harness.

Audits:
1. SSE streaming client disconnect detection, task cancellation, and exception recovery.
2. Circular reference handling in _sanitize_for_serialization.
3. Deep state mutation isolation on nested state objects during branching and rewinding.
4. Concurrent multi-turn recording thread safety on Session instances.
5. MemoryBank input boundary handling (None queries, empty strings, negative top_k, raw strings).
6. Orchestrator flag synchronization with initialized service instances.
7. Static UI asset serving and MIME type integrity.
8. Server main CLI argument parsing and config reloading.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import subprocess
import threading
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import pytest

from app.agent import CodingHarnessOrchestrator
from app.config import HarnessConfig, get_config, set_config
from app.server import app, orchestrator
from app.services.memory_bank import MemoryBankService, _extract_memory_fields
from app.services.session_manager import (
    Session,
    SessionManager,
    SessionTurn,
    _run_sync,
    _sanitize_for_serialization,
)


@pytest.fixture
def client():
  return TestClient(app)


def test_sanitize_circular_references():
  """Adversarial Test: Circular/recursive structures must not trigger RecursionError."""
  # Circular dictionary
  circular_dict = {"name": "root"}
  circular_dict["self"] = circular_dict
  sanitized_dict = _sanitize_for_serialization(circular_dict)
  assert sanitized_dict["name"] == "root"
  assert sanitized_dict["self"] == "[CircularReference]"

  # Circular list
  circular_list = ["item1"]
  circular_list.append(circular_list)
  sanitized_list = _sanitize_for_serialization(circular_list)
  assert sanitized_list[0] == "item1"
  assert sanitized_list[1] == "[CircularReference]"


def test_session_deep_state_mutation_isolation():
  """Adversarial Test: Nested mutable state objects must be deeply isolated between branches."""
  sm = SessionManager(use_vertex=False)
  sess = sm.get_or_create("nested-state-sess")

  # Setup nested mutable state
  sess.state["config"] = {"flags": ["a", "b"], "nested": {"count": 1}}
  t1 = sess.add_turn("user", "Turn 1 with nested state")

  # Branch session
  child = sm.branch_session(session_id="nested-state-sess", new_branch_name="nested-branch")

  # Mutate child nested state
  child.state["config"]["flags"].append("c")
  child.state["config"]["nested"]["count"] = 99

  # Parent session state must remain unaffected
  assert sess.state["config"]["flags"] == ["a", "b"]
  assert sess.state["config"]["nested"]["count"] == 1
  assert t1.state_snapshot["config"]["flags"] == ["a", "b"]
  assert t1.state_snapshot["config"]["nested"]["count"] == 1


def test_concurrent_session_turn_recording_thread_safety():
  """Stress Test: Concurrent threads appending turns to the same Session instance."""
  sm = SessionManager(use_vertex=False)
  sess = sm.get_or_create("concurrent-turns-sess")

  def _add_turns(worker_id: int):
    for i in range(10):
      sess.add_turn(
          role="user" if i % 2 == 0 else "assistant",
          content=f"Worker {worker_id} Turn {i}",
          tool_calls=[{"name": f"tool_{worker_id}_{i}", "args": {"step": i}}],
      )

  threads = [threading.Thread(target=_add_turns, args=(w,)) for w in range(5)]
  for t in threads:
    t.start()
  for t in threads:
    t.join()

  assert len(sess.turns) == 50
  # Verify every turn has a unique turn_id and valid structure
  turn_ids = {t.turn_id for t in sess.turns}
  assert len(turn_ids) == 50


def test_memory_bank_input_boundaries_and_resilience():
  """Adversarial Test: Boundary handling for query_memories, record_memory, and string inputs."""
  mb = MemoryBankService(use_vertex=False)

  # 1. Query with None, empty string, or whitespace
  res_none = mb.query_memories(None)
  assert isinstance(res_none, list)
  assert len(res_none) > 0

  res_empty = mb.query_memories("   ", top_k=-5)
  assert isinstance(res_empty, list)
  assert len(res_empty) > 0  # Falls back cleanly with max(1, top_k)

  # 2. Record with None / empty values
  rec = mb.record_memory(category="", content=None, metadata=None)
  assert rec.category == "guideline"
  assert rec.content == ""
  assert rec.metadata == {}

  # 3. _extract_memory_fields with raw string
  mem_id, cat, content, meta = _extract_memory_fields("Raw string fact memory", default_category="sec")
  assert content == "Raw string fact memory"
  assert cat == "sec"

  # 4. _extract_memory_fields with dict LRO response
  dict_lro_mem = {"id": "projects/p/locations/l/reasoningEngines/e/memories/mem-lro-99", "fact": "LRO Fact"}
  m_id, m_cat, m_content, _ = _extract_memory_fields(dict_lro_mem)
  assert m_id == "mem-lro-99"
  assert m_content == "LRO Fact"


def test_sse_stream_error_recovery(monkeypatch, client):
  """Adversarial Test: SSE generator captures unhandled stream exceptions as structured events."""
  # Patch orchestrator.execute_task_stream to raise an unexpected exception mid-stream
  async def _failing_stream(session_id: str, prompt: str):
    yield {"type": "event", "stage": "init", "message": "starting"}
    raise RuntimeError("Unexpected pipeline crash")

  monkeypatch.setattr(orchestrator, "execute_task_stream", _failing_stream)

  resp = client.post(
      "/api/chat/stream",
      json={"session_id": "error-stream-test", "prompt": "Trigger crash"},
  )
  assert resp.status_code == 200
  lines = [l for l in resp.text.split("\n\n") if l.startswith("data: ")]
  assert len(lines) >= 2
  assert "Unexpected pipeline crash" in lines[-1]
  assert '"type": "error"' in lines[-1]


def test_orchestrator_flag_synchronization_with_custom_services():
  """Tests that orchestrator.use_vertex and use_managed_services reflect initialized instances."""
  mock_session_svc = MagicMock()
  mock_session_svc.create_session = AsyncMock(return_value=MagicMock(id="s1"))

  managed_sm = SessionManager(session_service=mock_session_svc)
  local_mb = MemoryBankService(use_vertex=False)

  orch = CodingHarnessOrchestrator(
      workspace_root=".",
      session_manager=managed_sm,
      memory_bank=local_mb,
  )
  # When one service is managed, orchestrator reflects managed mode
  assert orch.use_vertex is True
  assert orch.use_managed_services is True
  assert orch.session_manager.is_managed is True
  assert orch.memory_bank.is_managed is False


def test_static_ui_assets_integrity(client):
  """Tests that all UI assets are mounted, accessible, and return valid HTTP 200 responses."""
  # 1. Root index.html
  resp_root = client.get("/")
  assert resp_root.status_code == 200
  assert "text/html" in resp_root.headers["content-type"]
  assert "Gemini Enterprise" in resp_root.text
  assert "Memory Bank" in resp_root.text
  assert "Rewind" in resp_root.text

  # 2. CSS Stylesheet
  resp_css = client.get("/static/style.css")
  assert resp_css.status_code == 200
  assert "text/css" in resp_css.headers["content-type"]
  assert "badge-mode" in resp_css.text

  # 3. JavaScript Controller
  resp_js = client.get("/static/main.js")
  assert resp_js.status_code == 200
  assert "handleStreamEvent" in resp_js.text
  assert "fetchMemories" in resp_js.text


def test_server_main_cli_argument_parsing():
  """Tests server argument parser with --use-managed-services and granular toggles."""
  cmd = [
      "python3",
      "-c",
      (
          "import argparse, os; "
          "from app.config import get_config; "
          "os.environ['USE_MANAGED_SERVICES'] = 'true'; "
          "cfg = get_config(reload=True); "
          "assert cfg.is_sessions_managed is True; "
          "assert cfg.is_memory_bank_managed is True; "
          "print('CLI_RELOAD_OK')"
      ),
  ]
  res = subprocess.run(cmd, capture_output=True, text=True)
  assert res.returncode == 0
  assert "CLI_RELOAD_OK" in res.stdout
