"""Tests for MemoryBankService dual backends (Local In-Memory and Vertex AI Memory Bank)."""

from unittest.mock import MagicMock
import pytest
from app.services.memory_bank import MemoryBankService, MemoryRecord


def test_memory_bank_local_mode():
  """Validates 100% offline local memory bank operations."""
  mb = MemoryBankService(use_vertex=False)
  assert mb.mode == "local"
  assert not mb.is_managed

  # Verify seeded enterprise guidelines
  seeded = mb.list_all()
  assert len(seeded) >= 4
  assert any("Async API Contract" in m["content"] for m in seeded)

  # Record a new memory
  new_rec = mb.record_memory(
      category="architecture",
      content="Always validate JSON schemas at boundary interfaces.",
      metadata={"source": "Unit Test Suite"},
  )
  assert isinstance(new_rec, MemoryRecord)
  assert new_rec.category == "architecture"

  # Query memories via keyword scoring
  results = mb.query_memories("JSON schemas", top_k=2)
  assert len(results) > 0
  assert results[0].content == (
      "Always validate JSON schemas at boundary interfaces."
  )


def test_memory_bank_managed_mode_with_mock():
  """Validates that managed mode properly constructs CreateMemoryRequest and RetrieveMemoriesRequest."""
  mock_client = MagicMock()

  # Mock CreateMemory response
  mock_created_mem = MagicMock()
  mock_created_mem.name = "projects/test-p/locations/us-central1/reasoningEngines/test-eng/memories/mem-uuid-101"
  mock_client.create_memory.return_value = mock_created_mem

  # Mock RetrieveMemories response
  mock_retrieved_proto = MagicMock()
  mock_retrieved_proto.memory.name = "projects/test-p/locations/us-central1/reasoningEngines/test-eng/memories/mem-uuid-202"
  mock_retrieved_proto.memory.fact = (
      "Distributed cache keys must include version prefix."
  )
  mock_retrieved_proto.memory.scope = {
      "category": "architecture",
      "app": "coding-harness",
  }
  mock_retrieved_proto.distance = 0.08

  mock_retrieve_resp = MagicMock()
  mock_retrieve_resp.retrieved_memories = [mock_retrieved_proto]
  mock_client.retrieve_memories.return_value = mock_retrieve_resp

  mb = MemoryBankService(
      client=mock_client,
      project_id="test-p",
      location="us-central1",
      agent_engine_id="test-eng",
  )
  assert mb.mode == "managed"
  assert mb.is_managed
  expected_parent = (
      "projects/test-p/locations/us-central1/reasoningEngines/test-eng"
  )
  assert mb.parent_path == expected_parent

  # 1. Test record_memory (CreateMemory)
  rec = mb.record_memory(
      category="architecture", content="Ensure non-blocking I/O"
  )
  mock_client.create_memory.assert_called_once()
  create_req = mock_client.create_memory.call_args.kwargs["request"]
  assert create_req.parent == expected_parent
  assert create_req.memory.fact == "Ensure non-blocking I/O"
  assert create_req.memory.scope["category"] == "architecture"
  assert create_req.memory.scope["app"] == "coding-harness"
  assert rec.memory_id == "mem-uuid-101"

  # 2. Test query_memories (RetrieveMemories)
  queried = mb.query_memories(
      "cache keys", category="architecture", top_k=3
  )
  mock_client.retrieve_memories.assert_called_once()
  ret_req = mock_client.retrieve_memories.call_args.kwargs["request"]
  assert ret_req.parent == expected_parent
  assert ret_req.scope["category"] == "architecture"
  assert ret_req.scope["app"] == "coding-harness"
  assert ret_req.similarity_search_params.search_query == "cache keys"
  assert ret_req.similarity_search_params.top_k == 3

  assert len(queried) == 1
  assert queried[0].memory_id == "mem-uuid-202"
  assert queried[0].content == (
      "Distributed cache keys must include version prefix."
  )
  assert queried[0].metadata["distance"] == 0.08
  assert queried[0].metadata["source"] == "Vertex AI Memory Bank"


def test_memory_bank_fallback_on_error():
  """Validates fallback to local keyword matching when Vertex AI raises an exception."""
  mock_client = MagicMock()
  mock_client.create_memory.side_effect = RuntimeError("Vertex AI Down")
  mock_client.retrieve_memories.side_effect = RuntimeError("Quota Exceeded")

  mb = MemoryBankService(client=mock_client)
  # Record should not crash; falls back to in-memory list
  rec = mb.record_memory(
      category="testing", content="Test fallback resilience rule"
  )
  assert rec.content == "Test fallback resilience rule"

  # Query should not crash; falls back to local keyword matching
  results = mb.query_memories("fallback resilience")
  assert any(r.content == "Test fallback resilience rule" for r in results)
