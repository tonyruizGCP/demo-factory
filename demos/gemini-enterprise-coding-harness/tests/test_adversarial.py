"""Adversarial stress and edge case test suite for Gemini Enterprise Coding Harness."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import pytest

from app.agent import CodingHarnessOrchestrator
from app.callbacks import prewalk_workspace_grounding
from app.config import HarnessConfig
from app.server import app, orchestrator
from app.services.memory_bank import MemoryBankService
from app.services.session_manager import Session, SessionManager, _run_sync
from app.services.workspace_context import WorkspaceContextService


@pytest.fixture
def client():
  return TestClient(app)


def test_adversarial_memory_bank_zero_matches_fallback():
  """Adversarial Test: Managed Memory Bank returns 0 matches for query.
  Must seamlessly fall back to seeded enterprise guidelines so agent is never ungrounded.
  """
  mock_client = MagicMock()
  mock_retrieve_resp = MagicMock()
  mock_retrieve_resp.retrieved_memories = []  # 0 matches from cloud similarity search
  mock_client.retrieve_memories.return_value = mock_retrieve_resp

  mb = MemoryBankService(client=mock_client, use_vertex=True)
  assert mb.mode == "managed"

  # Query memories: remote returns 0 items -> falls back to local seeded guidelines
  memories = mb.query_memories("async API architecture", top_k=3)
  mock_client.retrieve_memories.assert_called_once()
  assert len(memories) > 0
  assert any("Async API Contract" in m.content for m in memories)

  # Prewalk grounding with empty cloud engine still receives guidelines
  sm = SessionManager(use_vertex=False)
  sess = sm.get_or_create("adversarial-grounding-session")
  ws = WorkspaceContextService(".")
  grounding = prewalk_workspace_grounding(sess, mb, ws, "Refactor session store")
  assert len(grounding["relevant_guidelines"]) > 0
  assert any("Async" in g or "Linter" in g for g in grounding["relevant_guidelines"])


def test_adversarial_memory_bank_empty_list_memories_fallback():
  """Adversarial Test: Managed Memory Bank list_memories returns empty list.
  list_all() must fall back to seeded enterprise guidelines instead of returning an empty UI.
  """
  mock_client = MagicMock()
  # Mock a GAPIC pager or response with 0 memories
  mock_list_resp = MagicMock()
  mock_list_resp.memories = []
  mock_list_resp.__iter__ = MagicMock(return_value=iter([]))
  mock_client.list_memories.return_value = mock_list_resp

  mb = MemoryBankService(client=mock_client, use_vertex=True)
  assert mb.mode == "managed"

  all_mems = mb.list_all()
  assert len(all_mems) >= 4
  assert any("Async API Contract" in m["content"] for m in all_mems)


def test_adversarial_session_tool_calls_and_outputs_serialization():
  """Adversarial Test: Session.add_turn must properly serialize complex tool_calls
  and tool_outputs into ADK FunctionCall and FunctionResponse parts.
  """
  mock_service = MagicMock()
  mock_adk_sess = MagicMock(id="adk-sess-tools-101")
  mock_service.create_session = AsyncMock(return_value=mock_adk_sess)
  mock_service.append_event = AsyncMock(return_value=None)

  sm = SessionManager(session_service=mock_service)
  sess = sm.get_or_create("adversarial-tools-session")

  # Add turn with tool calls and tool outputs
  complex_tool_calls = [
      {"name": "lsp_find_definition", "args": {"symbol": "SessionManager"}},
      {"name": "raw_tool", "parameters": {"mode": "strict"}},
      {"name": "scalar_tool", "args": "scalar_value"},  # Non-dict args
  ]
  complex_tool_outputs = [
      {"name": "lsp_find_definition", "output": {"file": "session_manager.py", "line": 42}},
      {"name": "dap_run_pytest", "output": "Ran 4 tests - PASSED"},  # String output
      {"name": "list_output", "response": ["item1", "item2"]},  # List response
  ]

  turn = sess.add_turn(
      role="assistant",
      content="Executed AST refactoring tools.",
      tool_calls=complex_tool_calls,
      tool_outputs=complex_tool_outputs,
  )

  # Check local record
  assert len(turn.tool_calls) == 3
  assert len(turn.tool_outputs) == 3

  # Check ADK Event serialization
  mock_service.append_event.assert_called_once()
  event = mock_service.append_event.call_args.kwargs["event"]
  assert event.author == "assistant"
  assert event.content.role == "model"

  # Parts should contain: text, 3 function calls, 3 function responses
  parts = event.content.parts
  assert len(parts) >= 7

  # Verify FunctionCall part
  fc_parts = [p for p in parts if p.function_call is not None]
  assert len(fc_parts) == 3
  assert fc_parts[0].function_call.name == "lsp_find_definition"
  assert fc_parts[0].function_call.args == {"symbol": "SessionManager"}

  # Verify FunctionResponse part
  fr_parts = [p for p in parts if p.function_response is not None]
  assert len(fr_parts) == 3
  assert fr_parts[0].function_response.name == "lsp_find_definition"
  assert fr_parts[0].function_response.response == {"file": "session_manager.py", "line": 42}
  # String output was safely wrapped as {"output": "Ran 4 tests - PASSED"}
  assert fr_parts[1].function_response.response == {"output": "Ran 4 tests - PASSED"}


def test_adversarial_session_rewind_event_synchronization():
  """Adversarial Test: Session.rewind_to_turn synchronizes rewind events to ADK backend."""
  mock_service = MagicMock()
  mock_adk_sess = MagicMock(id="adk-sess-rewind-102")
  mock_service.create_session = AsyncMock(return_value=mock_adk_sess)
  mock_service.append_event = AsyncMock(return_value=None)

  sm = SessionManager(session_service=mock_service)
  sess = sm.get_or_create("rewind-sync-session")

  t1 = sess.add_turn("user", "Turn 1")
  t2 = sess.add_turn("assistant", "Turn 2")
  mock_service.append_event.reset_mock()

  # Rewind to t1
  assert sess.rewind_to_turn(t1.turn_id) is True
  assert len(sess.turns) == 1

  # Check that rewind event was sent to ADK
  mock_service.append_event.assert_called_once()
  rewind_event = mock_service.append_event.call_args.kwargs["event"]
  assert rewind_event.author == "system"
  assert any("REWIND" in p.text for p in rewind_event.content.parts if p.text)


def test_adversarial_concurrent_session_creation():
  """Stress Test: Concurrent threads calling get_or_create for the same session ID.
  Must be thread-safe and call backend create_session exactly once.
  """
  mock_service = MagicMock()
  mock_adk_sess = MagicMock(id="adk-concurrent-id-777")

  async def _delayed_create(**kwargs):
    await asyncio.sleep(0.05)
    return mock_adk_sess

  mock_service.create_session = AsyncMock(side_effect=_delayed_create)

  sm = SessionManager(session_service=mock_service)

  created_sessions = []

  def _worker():
    s = sm.get_or_create("shared-concurrent-session-id")
    created_sessions.append(s)

  threads = [threading.Thread(target=_worker) for _ in range(8)]
  for t in threads:
    t.start()
  for t in threads:
    t.join()

  assert len(created_sessions) == 8
  first_sess = created_sessions[0]
  # All threads must receive the exact same session instance
  for s in created_sessions:
    assert s is first_sess
  # Backend create_session called exactly once
  assert mock_service.create_session.call_count == 1


def test_adversarial_api_validation_errors(client):
  """Adversarial Test: API endpoints handle invalid query params and unexpected payloads."""
  # 1. Chat stream with empty prompt
  resp = client.post("/api/chat/stream", json={"prompt": ""})
  assert resp.status_code == 400
  assert "Prompt cannot be empty" in resp.json()["detail"]

  resp_ws = client.post("/api/chat/stream", json={"prompt": "    "})
  assert resp_ws.status_code == 400

  # 2. Rewind with missing / empty turn_id
  resp_rewind_empty = client.post(
      "/api/session/test-session/rewind", json={"turn_id": ""}
  )
  assert resp_rewind_empty.status_code == 400

  resp_rewind_missing = client.post(
      "/api/session/test-session/rewind", json={"turn_id": "non-existent-turn-id"}
  )
  assert resp_rewind_missing.status_code == 404

  # 3. Add memory with empty content
  resp_mem_empty = client.post(
      "/api/memory", json={"category": "architecture", "content": ""}
  )
  assert resp_mem_empty.status_code == 400
  assert "content cannot be empty" in resp_mem_empty.json()["detail"]

  # 4. Get memory with search query filter
  resp_query = client.get("/api/memory?query=Async&top_k=2")
  assert resp_query.status_code == 200
  data = resp_query.json()
  assert "memories" in data
  assert len(data["memories"]) <= 2


def test_adversarial_async_timeout_graceful_handling():
  """Adversarial Test: _run_sync timeout handling prevents worker hanging."""
  async def _hang_forever():
    await asyncio.sleep(10.0)

  # _run_sync with short timeout raises TimeoutError
  from concurrent.futures import TimeoutError as FuturesTimeoutError
  with pytest.raises(FuturesTimeoutError):
    _run_sync(_hang_forever(), timeout=0.1)


def test_adversarial_config_precedence_combinations(monkeypatch):
  """Adversarial Test: Complex combinations of CLI flags vs environment variables."""
  # Env says TRUE, CLI says --no-managed-services -> CLI MUST WIN
  monkeypatch.setenv("USE_MANAGED_SERVICES", "true")
  cfg1 = HarnessConfig.from_env_and_args(["--no-managed-services"])
  assert cfg1.is_sessions_managed is False
  assert cfg1.is_memory_bank_managed is False

  # Env says FALSE, CLI says --use-managed-services -> CLI MUST WIN
  monkeypatch.setenv("USE_MANAGED_SERVICES", "false")
  monkeypatch.setenv("USE_MANAGED_SESSIONS", "false")
  cfg2 = HarnessConfig.from_env_and_args(["--use-managed-services"])
  assert cfg2.is_sessions_managed is True
  assert cfg2.is_memory_bank_managed is True

  # CLI granular override: --use-managed-services --no-managed-sessions
  cfg3 = HarnessConfig.from_env_and_args(["--use-managed-services", "--no-managed-sessions"])
  assert cfg3.is_sessions_managed is False
  assert cfg3.is_memory_bank_managed is True
