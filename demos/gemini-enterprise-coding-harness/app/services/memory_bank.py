"""Memory Bank Service for Gemini Enterprise Coding Harness.

Implements cross-session long-term memory retrieval and consolidation
matching Vertex AI Agent Engine Memory Bank specifications, with dual-backend support:
1. Local in-memory store with semantic keyword scoring (default, offline, zero-dependency)
2. Vertex AI Memory Bank (MemoryBankServiceClient from google.cloud.aiplatform_v1beta1)
"""

from dataclasses import dataclass, field
import datetime
import logging
import os
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


@dataclass
class MemoryRecord:
  memory_id: str
  category: str  # e.g., 'guideline', 'architecture', 'user_preference', 'bug_fix'
  content: str
  metadata: Dict[str, Any] = field(default_factory=dict)
  timestamp: str = field(
      default_factory=lambda: datetime.datetime.now(
          datetime.timezone.utc
      ).isoformat()
  )


def _extract_memory_fields(
    mem: Any, default_category: str = "guideline"
) -> tuple[str, str, str, Dict[str, Any]]:
  """Extracts (memory_id, category, content/fact, metadata) safely from proto, dict, string, or mock."""
  if mem is None:
    return str(uuid.uuid4())[:8], default_category, "", {}

  if isinstance(mem, str):
    return str(uuid.uuid4())[:8], default_category, mem, {}

  # 1. Extract memory_id and content
  if isinstance(mem, dict):
    raw_name = mem.get("name") or mem.get("id") or str(uuid.uuid4())[:8]
    content = mem.get("fact") if "fact" in mem else mem.get("content", "")
    raw_scope = mem.get("scope")
    extra_meta = mem.get("metadata", {})
  else:
    raw_name = getattr(mem, "name", None) or getattr(mem, "id", None) or str(uuid.uuid4())[:8]
    content = getattr(mem, "fact", None) if hasattr(mem, "fact") else getattr(mem, "content", "")
    raw_scope = getattr(mem, "scope", None)
    extra_meta = getattr(mem, "metadata", {})

  mem_id = raw_name.split("/")[-1] if isinstance(raw_name, str) else str(uuid.uuid4())[:8]
  fact_str = str(content) if content is not None else ""

  # 2. Extract category and scope metadata
  category = default_category
  scope_metadata: Dict[str, Any] = {}

  if isinstance(raw_scope, dict):
    category = raw_scope.get("category") or default_category
    scope_metadata = {str(k): v for k, v in raw_scope.items() if k != "category"}
  elif hasattr(raw_scope, "items"):  # Proto map container
    try:
      d = dict(raw_scope.items())
      category = d.get("category") or default_category
      scope_metadata = {str(k): v for k, v in d.items() if k != "category"}
    except Exception:
      category = default_category
  elif isinstance(raw_scope, str) and raw_scope.strip():
    category = raw_scope.strip()
  elif hasattr(raw_scope, "category"):
    category = getattr(raw_scope, "category") or default_category

  metadata: Dict[str, Any] = {}
  if isinstance(extra_meta, dict):
    metadata.update(extra_meta)
  if scope_metadata:
    metadata["scope"] = scope_metadata

  return mem_id, category, fact_str, metadata


class MemoryBankService:
  """Vertex AI Memory Bank client with offline high-fidelity semantic simulation."""

  def __init__(
      self,
      use_vertex: bool = False,
      project_id: Optional[str] = None,
      location: Optional[str] = None,
      agent_engine_id: Optional[str] = None,
      client: Optional[Any] = None,
  ):
    self.project_id = (
        project_id
        or os.environ.get("GCP_PROJECT")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or "truiz-agy-demo"
    )
    self.location = (
        location
        or os.environ.get("GOOGLE_CLOUD_LOCATION")
        or os.environ.get("GCP_LOCATION")
        or "us-central1"
    )
    self.agent_engine_id = (
        agent_engine_id
        or os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID")
        or os.environ.get("AGENT_ENGINE_ID")
        or "coding-harness-engine"
    )
    self._memories: List[MemoryRecord] = []
    self._seed_default_guidelines()

    self._managed_active = False
    self.client = None

    if use_vertex or client is not None:
      if client is not None:
        self.client = client
        self._managed_active = True
      else:
        try:
          from google.api_core.client_options import ClientOptions
          from google.cloud.aiplatform_v1beta1 import MemoryBankServiceClient

          client_options = None
          if self.location != "us-central1":
            client_options = ClientOptions(
                api_endpoint=f"{self.location}-aiplatform.googleapis.com"
            )
          self.client = MemoryBankServiceClient(client_options=client_options)
          self._managed_active = True
        except Exception as e:
          logger.warning(
              "Could not initialize MemoryBankServiceClient (%s). Falling back to local in-memory store.",
              e,
          )
          self._managed_active = False
          self.client = None

  @property
  def parent_path(self) -> str:
    """Returns the Reasoning Engine resource parent path for Memory Bank."""
    return f"projects/{self.project_id}/locations/{self.location}/reasoningEngines/{self.agent_engine_id}"

  @property
  def mode(self) -> str:
    """Returns 'managed' if Vertex AI Memory Bank is active, else 'local'."""
    return "managed" if self._managed_active else "local"

  @property
  def is_managed(self) -> bool:
    return self._managed_active

  @property
  def use_vertex(self) -> bool:
    return self._managed_active

  def _seed_default_guidelines(self):
    """Seed typical enterprise software engineering guidelines."""
    defaults = [
        (
            "architecture",
            (
                "Async API Contract: All database and external RPC calls must"
                " use non-blocking async clients (e.g., aiosqlite, httpx)."
            ),
            {"source": "Architecture Review Board", "importance": "high"},
        ),
        (
            "guideline",
            (
                "Linter & Type Checking: Strict Pyright / Ruff compliance"
                " required. No bare exceptions or unannotated public functions."
            ),
            {"source": "Engineering Standards", "importance": "high"},
        ),
        (
            "testing",
            (
                "Hermetic Tests: Unit tests must use mock fixtures rather than"
                " binding to live external network ports."
            ),
            {"source": "CI/CD Pipeline Rules", "importance": "medium"},
        ),
        (
            "bug_fix",
            (
                "Learned from Incident #402: Always sanitize and validate JSON"
                " payloads before passing to downstream queue workers."
            ),
            {"source": "Post-Mortem 2026-08", "importance": "high"},
        ),
    ]
    for cat, text, meta in defaults:
      self._memories.append(
          MemoryRecord(
              memory_id=str(uuid.uuid4())[:8],
              category=cat,
              content=text,
              metadata=meta,
          )
      )

  def query_memories(
      self, query: str, category: Optional[str] = None, top_k: int = 5
  ) -> List[MemoryRecord]:
    """Retrieves relevant memories using Vertex AI similarity search or local keyword matching."""
    query_clean = str(query or "").strip()
    top_k_clean = max(1, top_k)
    cat_filter = str(category).strip() if (category and str(category).strip()) else None

    if self._managed_active and self.client:
      try:
        from google.cloud.aiplatform_v1beta1 import types

        scope = {"app": "coding-harness"}
        if cat_filter:
          scope["category"] = cat_filter

        sim_params = types.RetrieveMemoriesRequest.SimilaritySearchParams(
            search_query=query_clean,
            top_k=top_k_clean,
        )
        request = types.RetrieveMemoriesRequest(
            parent=self.parent_path,
            scope=scope,
            similarity_search_params=sim_params,
        )
        response = self.client.retrieve_memories(request=request)
        records: List[MemoryRecord] = []
        for rm in getattr(response, "retrieved_memories", []):
          mem = getattr(rm, "memory", None)
          if mem is None:
            continue
          mem_id, cat, content, meta = _extract_memory_fields(
              mem, default_category=cat_filter or "guideline"
          )
          meta["distance"] = getattr(rm, "distance", 0.0)
          meta["source"] = "Vertex AI Memory Bank"
          records.append(
              MemoryRecord(
                  memory_id=mem_id,
                  category=cat,
                  content=content,
                  metadata=meta,
              )
          )
        if records:
          return records
        logger.info(
            "Vertex AI Memory Bank returned 0 matches for query '%s'. Falling back to local seeded guidelines.",
            query_clean,
        )
      except Exception as e:
        logger.warning(
            "RetrieveMemories RPC failed (%s). Falling back to local in-memory search.",
            e,
        )

    # Local in-memory keyword & semantic relevance filter (used in local mode or when remote returns 0 matches / fails)
    query_lower = query_clean.lower()
    terms = [t for t in query_lower.split() if len(t) > 2]

    scored = []
    for m in self._memories:
      if cat_filter and m.category != cat_filter:
        continue
      score = 0
      content_lower = m.content.lower()
      for t in terms:
        if t in content_lower:
          score += 1
      # Default base score for core guidelines
      if m.metadata.get("importance") == "high":
        score += 0.5
      scored.append((score, m))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:top_k_clean]]

  def record_memory(
      self,
      category: str,
      content: str,
      metadata: Optional[Dict[str, Any]] = None,
  ) -> MemoryRecord:
    """Consolidates a new insight or rule discovered during agent execution."""
    cat_clean = str(category or "").strip() or "guideline"
    content_clean = str(content or "").strip()

    sanitized_meta = (
        {str(k): v for k, v in metadata.items()}
        if isinstance(metadata, dict)
        else {}
    )
    rec = MemoryRecord(
        memory_id=str(uuid.uuid4())[:8],
        category=cat_clean,
        content=content_clean,
        metadata=sanitized_meta,
    )

    if self._managed_active and self.client:
      try:
        from google.cloud.aiplatform_v1beta1 import types

        scope = {"category": cat_clean, "app": "coding-harness"}
        memory_proto = types.Memory(
            fact=content_clean,
            scope=scope,
        )
        request = types.CreateMemoryRequest(
            parent=self.parent_path,
            memory=memory_proto,
        )
        response = self.client.create_memory(request=request)
        mem_obj = response
        try:
          from google.api_core import operation
          if isinstance(response, operation.Operation):
            mem_obj = response.result(timeout=10.0)
          elif hasattr(response, "result") and callable(response.result):
            res = response.result(timeout=10.0)
            if hasattr(res, "name") and isinstance(res.name, str):
              mem_obj = res
        except Exception as lro_err:
          logger.warning("Operation.result error or timeout (%s). Retaining generated ID.", lro_err)

        if isinstance(mem_obj, dict):
          name_val = mem_obj.get("name") or mem_obj.get("id")
          if name_val:
            rec.memory_id = str(name_val).split("/")[-1]
        elif hasattr(mem_obj, "name") and isinstance(mem_obj.name, str) and mem_obj.name:
          rec.memory_id = mem_obj.name.split("/")[-1]
      except Exception as e:
        logger.warning(
            "CreateMemory RPC failed (%s). Retaining local in-memory record.",
            e,
        )

    self._memories.append(rec)
    return rec

  def list_all(self) -> List[Dict[str, Any]]:
    """Lists all memories, from Vertex AI if active, or local cache."""
    if self._managed_active and self.client:
      try:
        from google.cloud.aiplatform_v1beta1 import types

        req = types.ListMemoriesRequest(parent=self.parent_path)
        response = self.client.list_memories(request=req)

        # Extract memories whether response is a ListMemoriesPager, iterable, or object with .memories
        if hasattr(response, "memories") and response.memories is not None:
          mems = list(response.memories)
        elif hasattr(response, "__iter__"):
          mems = list(response)
        else:
          mems = []

        if mems:
          out = []
          for m in mems:
            mem_id, cat, content, meta = _extract_memory_fields(m)
            meta["source"] = "Vertex AI Memory Bank"
            out.append({
                "id": mem_id,
                "category": cat,
                "content": content,
                "metadata": meta,
                "timestamp": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
            })
          if out:
            return out
      except Exception as e:
        logger.warning(
            "ListMemories RPC failed (%s). Falling back to local store.", e
        )

    return [
        {
            "id": m.memory_id,
            "category": m.category,
            "content": m.content,
            "metadata": m.metadata,
            "timestamp": m.timestamp,
        }
        for m in self._memories
    ]
