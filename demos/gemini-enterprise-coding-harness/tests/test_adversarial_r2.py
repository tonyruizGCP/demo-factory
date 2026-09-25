"""Round 2 Adversarial and Edge-Case Test Suite for Gemini Enterprise Coding Harness.

Probes:
1. Tool call and output serialization with non-dict, non-serializable, and nested objects (sets, bytes, custom classes, exceptions).
2. Session branching from specific turn, non-existent turn rejection, branch name collision disambiguation, and mutation isolation.
3. Memory bank non-standard scope parsing, missing keys, dict inputs, and metadata preservation.
4. Shell script execution, flag variations (space vs =), and bash -u safety.
5. Backward compatibility across existing constructor signatures and unmanaged invocation.
"""

import datetime
import os
import subprocess
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import pytest

from app.agent import CodingHarnessOrchestrator
from app.config import HarnessConfig
from app.server import app, orchestrator
from app.services.memory_bank import MemoryBankService, _extract_memory_fields
from app.services.session_manager import Session, SessionManager, _sanitize_for_serialization


@pytest.fixture
def client():
  return TestClient(app)


class CustomClass:
  def __init__(self, key, value):
    self.key = key
    self.value = value


def test_sanitize_for_serialization_complex_objects():
  """Tests that _sanitize_for_serialization converts non-JSON types safely."""
  sample_data = {
      "bytes": b"hello binary",
      "set": {3, 1, 2},
      "date": datetime.date(2026, 9, 3),
      "datetime": datetime.datetime(2026, 9, 3, 12, 0, 0, tzinfo=datetime.timezone.utc),
      "exception": ValueError("Invalid value"),
      "custom_obj": CustomClass("foo", "bar"),
      "nested": [
          {"inner_set": {"z", "a"}},
          b"nested binary",
      ],
  }
  sanitized = _sanitize_for_serialization(sample_data)

  assert sanitized["bytes"] == "hello binary"
  assert sanitized["set"] == [1, 2, 3]
  assert sanitized["date"] == "2026-09-03"
  assert "2026-09-03T12:00:00" in sanitized["datetime"]
  assert sanitized["exception"] == {"error_type": "ValueError", "message": "Invalid value"}
  assert sanitized["custom_obj"] == {"key": "foo", "value": "bar"}
  assert sanitized["nested"][0]["inner_set"] == ["a", "z"]
  assert sanitized["nested"][1] == "nested binary"


def test_tool_serialization_with_non_dict_and_non_serializable():
  """Adversarial Test: Tool calls and outputs with non-dict objects and non-serializable values."""
  mock_service = MagicMock()
  mock_adk_sess = MagicMock(id="adk-sess-r2")
  mock_service.create_session = AsyncMock(return_value=mock_adk_sess)
  mock_service.append_event = AsyncMock(return_value=None)

  sm = SessionManager(session_service=mock_service)
  sess = sm.get_or_create("sess-tools-r2")

  tool_calls = [
      {"name": "valid_tool", "args": {"files": {"a.py", "b.py"}, "blob": b"data"}},
      "scalar_tool_name",
      CustomClass("tool_class", 42),
  ]
  tool_outputs = [
      {"name": "valid_tool", "output": {"results": {10, 20}, "err": RuntimeError("failed")}},
      "Raw string output",
      RuntimeError("Tool execution crash"),
  ]

  turn = sess.add_turn(
      role="assistant",
      content="Tools processed.",
      tool_calls=tool_calls,
      tool_outputs=tool_outputs,
  )

  # Check local normalization
  assert len(turn.tool_calls) == 3
  assert all(isinstance(tc, dict) for tc in turn.tool_calls)
  assert turn.tool_calls[0]["args"]["files"] == ["a.py", "b.py"]
  assert turn.tool_calls[0]["args"]["blob"] == "data"
  assert turn.tool_calls[1]["name"] == "tool_call"
  assert turn.tool_calls[1]["args"]["raw"] == "scalar_tool_name"

  assert len(turn.tool_outputs) == 3
  assert all(isinstance(to, dict) for to in turn.tool_outputs)
  assert turn.tool_outputs[0]["output"]["results"] == [10, 20]
  assert turn.tool_outputs[0]["output"]["err"]["error_type"] == "RuntimeError"
  assert turn.tool_outputs[1]["output"] == "Raw string output"
  assert turn.tool_outputs[2]["output"]["error_type"] == "RuntimeError"

  # Check ADK Event serialization
  mock_service.append_event.assert_called_once()
  event = mock_service.append_event.call_args.kwargs["event"]
  parts = event.content.parts

  # FunctionCall parts
  fc_parts = [p for p in parts if p.function_call is not None]
  assert len(fc_parts) == 3
  # FunctionResponse parts
  fr_parts = [p for p in parts if p.function_response is not None]
  assert len(fr_parts) == 3


def test_session_branching_and_isolation():
  """Tests session branching from specific turns, collision disambiguation, and turn isolation."""
  sm = SessionManager(use_vertex=False)
  sess = sm.get_or_create("sess-parent")

  sess.state["checkpoint"] = "cp1"
  t1 = sess.add_turn("user", "Turn 1", tool_calls=[], tool_outputs=[{"name": "t1", "output": "out1"}])
  sess.state["checkpoint"] = "cp2"
  t2 = sess.add_turn("assistant", "Turn 2", tool_calls=[], tool_outputs=[])
  sess.state["checkpoint"] = "cp3"
  t3 = sess.add_turn("user", "Turn 3", tool_calls=[], tool_outputs=[])

  # 1. Branch from specific turn t1
  child = sm.branch_session(session_id="sess-parent", new_branch_name="feature-a", from_turn_id=t1.turn_id)
  assert child.session_id == "sess-parent-branch-feature-a"
  assert child.parent_session_id == "sess-parent"
  assert child.branch_name == "feature-a"
  assert len(child.turns) == 1
  assert child.turns[0].turn_id == t1.turn_id
  assert child.state["checkpoint"] == "cp1"

  # 2. Test turn mutation isolation: mutating child turn does not mutate parent turn
  child.turns[0].content = "MUTATED"
  child.turns[0].tool_outputs[0]["output"] = "MUTATED_OUT"
  assert sess.turns[0].content == "Turn 1"
  assert sess.turns[0].tool_outputs[0]["output"] == "out1"

  # 3. Branch collision handling: branching again with same name disambiguates session_id
  child_collision = sm.branch_session(session_id="sess-parent", new_branch_name="feature-a")
  assert child_collision.session_id == "sess-parent-branch-feature-a-1"
  assert child_collision.session_id in sm._sessions

  child_collision_2 = sm.branch_session(session_id="sess-parent", new_branch_name="feature-a")
  assert child_collision_2.session_id == "sess-parent-branch-feature-a-2"

  # 4. Branching from non-existent turn raises ValueError
  with pytest.raises(ValueError, match="not found"):
    sm.branch_session(session_id="sess-parent", new_branch_name="bad-branch", from_turn_id="invalid-turn-id")

  # 5. Branching from empty branch name raises ValueError
  with pytest.raises(ValueError, match="Branch name cannot be empty"):
    sm.branch_session(session_id="sess-parent", new_branch_name="   ")

  # 6. Branching from non-existent session raises KeyError
  with pytest.raises(KeyError, match="not found"):
    sm.branch_session(session_id="non-existent-session", new_branch_name="any-branch")


def test_session_branch_api_endpoint(client):
  """Tests POST /api/session/{id}/branch endpoint."""
  # Create a session with turns
  resp_chat = client.post(
      "/api/chat/stream",
      json={"session_id": "api-branch-test", "prompt": "Hello world"},
  )
  assert resp_chat.status_code == 200

  # Get turns
  resp_sess = client.get("/api/session/api-branch-test")
  assert resp_sess.status_code == 200
  turns = resp_sess.json()["turns"]
  first_turn_id = turns[0]["turn_id"]

  # Successful branch
  resp_branch = client.post(
      "/api/session/api-branch-test/branch",
      json={"branch_name": "experiment-1", "from_turn_id": first_turn_id},
  )
  assert resp_branch.status_code == 200
  data = resp_branch.json()
  assert data["status"] == "BRANCHED"
  assert data["branch"] == "experiment-1"
  assert data["turn_count"] == 1
  assert data["parent_session_id"] == "api-branch-test"

  # Branch with invalid turn_id -> 404
  resp_bad_turn = client.post(
      "/api/session/api-branch-test/branch",
      json={"branch_name": "experiment-2", "from_turn_id": "non-existent-turn"},
  )
  assert resp_bad_turn.status_code == 404

  # Branch with empty name -> 400
  resp_empty_name = client.post(
      "/api/session/api-branch-test/branch",
      json={"branch_name": "  "},
  )
  assert resp_empty_name.status_code == 400

  # Branch on unknown session -> 404
  resp_unknown_sess = client.post(
      "/api/session/unknown-session-xyz/branch",
      json={"branch_name": "any"},
  )
  assert resp_unknown_sess.status_code == 404


def test_memory_bank_scope_parsing_and_metadata():
  """Tests _extract_memory_fields and MemoryBankService with diverse scope and metadata structures."""
  # 1. Non-standard scope dictionary (extra keys, missing category)
  mock_proto_1 = MagicMock()
  mock_proto_1.name = "projects/p/locations/l/reasoningEngines/e/memories/mem-101"
  mock_proto_1.fact = "Always use hermetic tests"
  mock_proto_1.scope = {"app": "coding-harness", "team": "devai", "framework": "fastapi"}
  mock_proto_1.metadata = {"creator": "tony"}

  mem_id, cat, content, meta = _extract_memory_fields(mock_proto_1, default_category="architecture")
  assert mem_id == "mem-101"
  assert cat == "architecture"  # Fallback to default when 'category' key not in scope
  assert content == "Always use hermetic tests"
  assert meta["creator"] == "tony"
  assert meta["scope"] == {"app": "coding-harness", "team": "devai", "framework": "fastapi"}

  # 2. String scope
  mock_proto_2 = MagicMock()
  mock_proto_2.name = "mem-102"
  mock_proto_2.fact = "Use strong typing"
  mock_proto_2.scope = "quality"
  mem_id, cat, content, meta = _extract_memory_fields(mock_proto_2)
  assert cat == "quality"
  assert content == "Use strong typing"

  # 3. Dict memory object (from REST API or JSON fixture)
  dict_mem = {
      "name": "mem-103",
      "fact": "Sanitize shell inputs",
      "scope": {"category": "security", "level": "critical"},
  }
  mem_id, cat, content, meta = _extract_memory_fields(dict_mem)
  assert mem_id == "mem-103"
  assert cat == "security"
  assert content == "Sanitize shell inputs"
  assert meta["scope"] == {"level": "critical"}

  # 4. None / Empty fact
  mock_proto_empty = MagicMock()
  mock_proto_empty.name = "mem-104"
  mock_proto_empty.fact = None
  mock_proto_empty.scope = None
  mem_id, cat, content, meta = _extract_memory_fields(mock_proto_empty)
  assert mem_id == "mem-104"
  assert content == ""
  assert cat == "guideline"


def test_run_demo_shell_script_argument_parsing():
  """Tests run_demo.sh flag parsing, spaces in arguments, and nounset safety."""
  project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  script_path = os.path.join(project_root, "run_demo.sh")

  # Test 1: Space-separated arguments
  cmd_spaces = [
      "bash",
      "-u",
      script_path,
      "--port",
      "9191",
      "--project-id",
      "project-with-spaces-test",
      "--location",
      "us-east4",
      "--agent-engine-id",
      "engine-test-1",
      "--use-managed-services",
  ]
  env = dict(os.environ, DRY_RUN="1")
  result = subprocess.run(cmd_spaces, capture_output=True, text=True, env=env)
  assert result.returncode == 0
  assert "Port:               9191" in result.stdout
  assert "Project ID:         project-with-spaces-test" in result.stdout
  assert "Location:           us-east4" in result.stdout
  assert "Agent Engine ID:    engine-test-1" in result.stdout
  assert "Managed Services:   true" in result.stdout

  # Test 2: Equal-separated arguments
  cmd_equals = [
      "bash",
      "-u",
      script_path,
      "--port=9292",
      "--project-id=project-eq-test",
      "--use-managed-sessions",
      "--no-managed-memory-bank",
  ]
  result_eq = subprocess.run(cmd_equals, capture_output=True, text=True, env=env)
  assert result_eq.returncode == 0
  assert "Port:               9292" in result_eq.stdout
  assert "Project ID:         project-eq-test" in result_eq.stdout
  assert "Managed Sessions:   true" in result_eq.stdout
  assert "Managed MemoryBank: false" in result_eq.stdout


def test_backward_compatibility_constructors_and_signatures():
  """Ensures all original classes and methods can be instantiated with original legacy signatures."""
  # 1. CodingHarnessOrchestrator legacy keyword arguments
  orch = CodingHarnessOrchestrator(
      workspace_root=".",
      use_vertex=False,
      project_id="legacy-proj",
      location="us-central1",
      agent_engine_id="legacy-engine",
  )
  assert orch.session_manager.mode == "local"
  assert orch.memory_bank.mode == "local"

  # 2. SessionManager legacy constructor
  sm = SessionManager(
      use_vertex=False,
      project_id="test-proj",
      location="us-central1",
      agent_engine_id="test-engine",
  )
  assert sm.mode == "local"
  sess = sm.get_or_create("legacy-sess")

  # 3. Session.branch with single argument
  child_sess = sess.branch("my-branch")
  assert child_sess.branch_name == "my-branch"

  # 4. MemoryBankService legacy query and record
  mb = MemoryBankService(use_vertex=False)
  mem = mb.record_memory(category="architecture", content="Test guideline", metadata={"test": True})
  assert mem.category == "architecture"
  queried = mb.query_memories(query="Test", top_k=2)
  assert len(queried) > 0
