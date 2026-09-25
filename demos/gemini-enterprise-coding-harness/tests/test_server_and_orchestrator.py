"""Tests for FastAPI endpoints and CodingHarnessOrchestrator."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import pytest
from app.agent import CodingHarnessOrchestrator
from app.server import app, orchestrator
from app.services.memory_bank import MemoryBankService
from app.services.session_manager import SessionManager


@pytest.fixture
def client():
  return TestClient(app)


def test_orchestrator_local_mode():
  """Validates orchestrator initialization with 100% offline local services."""
  orch = CodingHarnessOrchestrator(
      workspace_root=".",
      use_managed_services=False,
      use_managed_sessions=False,
      use_managed_memory_bank=False,
  )
  assert orch.session_manager.mode == "local"
  assert orch.memory_bank.mode == "local"


def test_orchestrator_stream_execution():
  """Validates full SSE task stream generation using in-memory services."""
  async def _run():
    orch = CodingHarnessOrchestrator(
        workspace_root=".",
        use_managed_services=False,
        use_managed_sessions=False,
        use_managed_memory_bank=False,
    )
    events = []
    async for item in orch.execute_task_stream(
        "test-session", "Refactor SessionManager async"
    ):
      events.append(item)

    event_types = [e.get("type") for e in events]
    assert "event" in event_types
    assert "prewalk_complete" in event_types
    assert "thought" in event_types
    assert "tool_call" in event_types
    assert "final_response" in event_types

    session = orch.session_manager.get_or_create("test-session")
    assert len(session.turns) >= 2

  asyncio.run(_run())


def test_api_status_endpoint(client):
  """Validates /api/status returns service health and backend modes."""
  resp = client.get("/api/status")
  assert resp.status_code == 200
  data = resp.json()
  assert data["status"] == "HEALTHY"
  assert data["mode"] in ("local", "managed")
  assert "sessions" in data["services"]
  assert "memory_bank" in data["services"]
  assert data["services"]["sessions"]["mode"] in ("local", "managed")
  assert data["services"]["memory_bank"]["mode"] in ("local", "managed")


def test_api_session_and_rewind_endpoints(client):
  """Validates /api/session/{id} and rewind endpoint with mode indicator."""
  # Get session
  resp = client.get("/api/session/test-api-session")
  assert resp.status_code == 200
  data = resp.json()
  assert data["session_id"] == "test-api-session"
  assert "mode" in data
  assert data["mode"] in ("local", "managed")
  assert "branch" in data
  assert "turns" in data

  # Add turns to test session
  sess = orchestrator.session_manager.get_or_create("test-api-session")
  t1 = sess.add_turn("user", "Initial prompt")
  t2 = sess.add_turn("assistant", "Response")

  # Rewind to t1
  rewind_resp = client.post(
      "/api/session/test-api-session/rewind", json={"turn_id": t1.turn_id}
  )
  assert rewind_resp.status_code == 200
  rewind_data = rewind_resp.json()
  assert rewind_data["status"] == "REWOUND"
  assert "mode" in rewind_data


def test_api_memory_endpoints(client):
  """Validates /api/memory GET and POST endpoints with mode indicator."""
  # GET memories
  get_resp = client.get("/api/memory")
  assert get_resp.status_code == 200
  data = get_resp.json()
  assert "mode" in data
  assert data["mode"] in ("local", "managed")
  assert "memories" in data
  assert len(data["memories"]) >= 4

  # POST new memory
  post_resp = client.post(
      "/api/memory",
      json={
          "category": "architecture",
          "content": "Verify SSE keep-alive heartbeats",
      },
  )
  assert post_resp.status_code == 200
  post_data = post_resp.json()
  assert post_data["status"] == "RECORDED"
  assert "mode" in post_data
  assert "memory_id" in post_data


def test_api_managed_mode_indicators(monkeypatch, client):
  """Validates that endpoints return 'managed' mode when services are managed."""
  mock_session_svc = MagicMock()
  mock_session_svc.create_session = AsyncMock(
      return_value=MagicMock(id="managed-s-1")
  )
  mock_session_svc.append_event = AsyncMock(return_value=None)

  mock_mb_client = MagicMock()
  mock_mb_client.create_memory.return_value = MagicMock(
      name="projects/p/locations/l/reasoningEngines/re/memories/m1"
  )
  mock_mb_client.retrieve_memories.return_value = MagicMock(
      retrieved_memories=[]
  )

  managed_sm = SessionManager(session_service=mock_session_svc)
  managed_mb = MemoryBankService(client=mock_mb_client)

  # Temporarily point orchestrator services to managed
  monkeypatch.setattr(orchestrator, "session_manager", managed_sm)
  monkeypatch.setattr(orchestrator, "memory_bank", managed_mb)

  # Check /api/status
  status_resp = client.get("/api/status")
  assert status_resp.status_code == 200
  status_data = status_resp.json()
  assert status_data["mode"] == "managed"
  assert status_data["services"]["sessions"]["mode"] == "managed"
  assert status_data["services"]["memory_bank"]["mode"] == "managed"

  # Check /api/memory
  mem_resp = client.get("/api/memory")
  assert mem_resp.status_code == 200
  assert mem_resp.json()["mode"] == "managed"

  # Check /api/session/{id}
  sess_resp = client.get("/api/session/new-managed-test")
  assert sess_resp.status_code == 200
  assert sess_resp.json()["mode"] == "managed"


def test_orchestrator_managed_stream_execution():
  """Validates end-to-end task stream execution with mocked managed session & memory bank backends."""
  mock_session_svc = MagicMock()
  mock_adk_sess = MagicMock(id="managed-orch-session-id")
  mock_session_svc.create_session = AsyncMock(return_value=mock_adk_sess)
  mock_session_svc.append_event = AsyncMock(return_value=None)

  mock_mb_client = MagicMock()
  mock_mb_client.create_memory.return_value = MagicMock(
      name="projects/p/locations/l/reasoningEngines/re/memories/m-consolidated-1"
  )
  mock_retrieved_mem = MagicMock()
  mock_retrieved_mem.memory.name = "projects/p/locations/l/reasoningEngines/re/memories/m-prewalk-1"
  mock_retrieved_mem.memory.fact = "Managed Prewalk Rule: All tests must run in isolated sandboxes."
  mock_retrieved_mem.memory.scope = {"category": "architecture", "app": "coding-harness"}
  mock_retrieved_mem.distance = 0.05
  mock_mb_client.retrieve_memories.return_value = MagicMock(
      retrieved_memories=[mock_retrieved_mem]
  )

  managed_sm = SessionManager(session_service=mock_session_svc)
  managed_mb = MemoryBankService(client=mock_mb_client)

  orch = CodingHarnessOrchestrator(
      workspace_root=".",
      session_manager=managed_sm,
      memory_bank=managed_mb,
  )
  assert orch.session_manager.mode == "managed"
  assert orch.memory_bank.mode == "managed"

  async def _run():
    events = []
    async for item in orch.execute_task_stream(
        "managed-orch-session", "Refactor SessionManager async"
    ):
      events.append(item)

    # 1. Prewalk queried memory bank
    mock_mb_client.retrieve_memories.assert_called_once()
    prewalk_event = next(e for e in events if e.get("type") == "prewalk_complete")
    guidelines = prewalk_event["grounding"]["relevant_guidelines"]
    assert any("Managed Prewalk Rule" in g for g in guidelines)

    # 2. Session created in managed backend
    mock_session_svc.create_session.assert_called_once()

    # 3. Consolidation recorded new memory
    mock_mb_client.create_memory.assert_called_once()

    # 4. Turns appended to managed session
    assert mock_session_svc.append_event.call_count >= 2

  asyncio.run(_run())
