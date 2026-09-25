"""Tests for SessionManager and Session service backends."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from app.services.session_manager import Session, SessionManager


def test_session_manager_local_mode():
  """Validates 100% offline local session lifecycle with turns, rewind, and branch."""
  sm = SessionManager(use_vertex=False)
  assert sm.mode == "local"
  assert not sm.is_managed

  sess = sm.get_or_create("demo-session-local")
  assert sess.session_id == "demo-session-local"
  assert len(sess.turns) == 0

  # 1. Turn addition
  t1 = sess.add_turn(role="user", content="Refactor SessionManager")
  sess.state["active_file"] = "app/services/session_manager.py"
  t2 = sess.add_turn(
      role="assistant",
      content="Analyzing AST...",
      tool_calls=[{"name": "lsp_find_definition", "args": {}}],
  )
  assert len(sess.turns) == 2
  assert sess.turns[0].content == "Refactor SessionManager"
  assert sess.turns[1].tool_calls[0]["name"] == "lsp_find_definition"

  # 2. Rewind verification
  assert sess.rewind_to_turn(t1.turn_id) is True
  assert len(sess.turns) == 1
  assert sess.turns[0].turn_id == t1.turn_id
  assert sess.rewind_to_turn("nonexistent-turn") is False

  # 3. Branching verification
  branch_sess = sess.branch("feature-ast")
  assert "feature-ast" in branch_sess.session_id
  assert branch_sess.branch_name == "feature-ast"
  assert branch_sess.parent_session_id == sess.session_id
  assert len(branch_sess.turns) == 1


def test_session_manager_managed_mode_with_mock():
  """Validates that managed mode routes creation and turn events through VertexAiSessionService."""
  mock_service = MagicMock()
  mock_adk_sess = MagicMock()
  mock_adk_sess.id = "vertex-sess-uuid-999"
  mock_service.create_session = AsyncMock(return_value=mock_adk_sess)
  mock_service.append_event = AsyncMock(return_value=None)

  sm = SessionManager(session_service=mock_service)
  assert sm.mode == "managed"
  assert sm.is_managed

  # Session creation triggers ADK create_session
  sess = sm.get_or_create("managed-session-1")
  mock_service.create_session.assert_called_once()
  create_kwargs = mock_service.create_session.call_args.kwargs
  assert create_kwargs["app_name"] == "coding-harness"
  assert create_kwargs["user_id"] == "default-user"
  assert create_kwargs["state"]["harness_session_id"] == "managed-session-1"
  assert sess.adk_session == mock_adk_sess

  # Turn addition triggers ADK append_event
  t = sess.add_turn(role="user", content="Deploy managed microservice")
  assert len(sess.turns) == 1
  mock_service.append_event.assert_called_once()
  append_kwargs = mock_service.append_event.call_args.kwargs
  assert append_kwargs["session"] == mock_adk_sess
  event = append_kwargs["event"]
  assert event.author == "user"
  assert event.content.parts[0].text == "Deploy managed microservice"

  # Listing shows managed IDs
  sessions_list = sm.list_sessions()
  assert len(sessions_list) == 1
  assert sessions_list[0]["managed_id"] == "vertex-sess-uuid-999"
  assert sessions_list[0]["mode"] == "managed"


def test_session_manager_managed_fallback_on_error():
  """Validates graceful degradation to in-memory sessions if Vertex AI raises errors."""
  mock_service = MagicMock()
  mock_service.create_session = AsyncMock(
      side_effect=RuntimeError("GCP Connection Timeout")
  )
  mock_service.append_event = AsyncMock(
      side_effect=RuntimeError("Quota Exceeded")
  )

  sm = SessionManager(session_service=mock_service)
  # get_or_create should not crash; it logs a warning and creates a local session
  sess = sm.get_or_create("faulty-session")
  assert sess.session_id == "faulty-session"

  # add_turn should not crash
  turn = sess.add_turn(role="user", content="Test fallback")
  assert turn.content == "Test fallback"
  assert len(sess.turns) == 1
