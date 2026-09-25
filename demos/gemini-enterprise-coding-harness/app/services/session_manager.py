"""Session Manager Service for Gemini Enterprise Coding Harness.

Implements turn history, state snapshots, session branching, and rewind/replay
capabilities, with seamless dual-backend support:
1. Local in-memory session engine (default, offline, zero-dependency)
2. Gemini Enterprise / ADK VertexAiSessionService managed persistence
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import contextvars
import copy
from dataclasses import dataclass, field
import datetime
import inspect
import logging
import os
import threading
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="adk_session_worker")


def _run_sync(coro, timeout: float = 30.0):
  """Executes an async coroutine synchronously, handling active event loops safely."""
  try:
    loop = asyncio.get_running_loop()
  except RuntimeError:
    loop = None

  if loop is not None and loop.is_running():
    def _worker():
      new_loop = asyncio.new_event_loop()
      try:
        asyncio.set_event_loop(new_loop)
        return new_loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
      finally:
        new_loop.close()

    ctx = contextvars.copy_context()
    return _executor.submit(ctx.run, _worker).result(timeout=timeout)

  async def _runner():
    return await asyncio.wait_for(coro, timeout=timeout)

  return asyncio.run(_runner())


def _invoke_maybe_async(fn, *args, **kwargs):
  """Invokes a callable, awaiting it via _run_sync if it returns a coroutine."""
  res = fn(*args, **kwargs)
  if inspect.iscoroutine(res):
    return _run_sync(res)
  return res


def _sanitize_for_serialization(obj: Any, seen: Optional[set] = None) -> Any:
  """Recursively sanitizes values for JSON/proto serialization, handling circular references."""
  if obj is None or isinstance(obj, (str, int, float, bool)):
    return obj

  if seen is None:
    seen = set()
  obj_id = id(obj)
  if isinstance(obj, (dict, list, tuple, set, frozenset)) or hasattr(obj, "__dict__"):
    if obj_id in seen:
      return "[CircularReference]"
    seen.add(obj_id)

  if isinstance(obj, bytes):
    return obj.decode("utf-8", errors="replace")
  if isinstance(obj, (set, frozenset)):
    try:
      return sorted([_sanitize_for_serialization(x, seen) for x in obj])
    except TypeError:
      return [_sanitize_for_serialization(x, seen) for x in obj]
  if isinstance(obj, (list, tuple)):
    return [_sanitize_for_serialization(x, seen) for x in obj]
  if isinstance(obj, dict):
    return {str(k): _sanitize_for_serialization(v, seen) for k, v in obj.items()}
  if isinstance(obj, (datetime.date, datetime.datetime)):
    return obj.isoformat()
  if isinstance(obj, BaseException):
    return {"error_type": obj.__class__.__name__, "message": str(obj)}
  if hasattr(obj, "__dict__"):
    try:
      return {str(k): _sanitize_for_serialization(v, seen) for k, v in obj.__dict__.items()}
    except Exception:
      return str(obj)
  return str(obj)


@dataclass
class SessionTurn:
  turn_id: str
  role: str
  content: str
  tool_calls: List[Dict[str, Any]] = field(default_factory=list)
  tool_outputs: List[Dict[str, Any]] = field(default_factory=list)
  timestamp: str = field(
      default_factory=lambda: datetime.datetime.now(
          datetime.timezone.utc
      ).isoformat()
  )
  state_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
  """Harness session encapsulating trajectory, turns, and optional ADK persistence."""

  session_id: str
  turns: List[SessionTurn] = field(default_factory=list)
  state: Dict[str, Any] = field(default_factory=dict)
  parent_session_id: Optional[str] = None
  branch_name: str = "main"
  adk_session: Optional[Any] = None
  session_service: Optional[Any] = None
  app_name: str = "coding-harness"
  user_id: str = "default-user"
  _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

  def add_turn(
      self,
      role: str,
      content: str,
      tool_calls: Optional[List[Dict[str, Any]]] = None,
      tool_outputs: Optional[List[Dict[str, Any]]] = None,
  ) -> SessionTurn:
    """Records a new turn locally and synchronizes to VertexAiSessionService if managed."""
    content_clean = str(content or "")

    # Normalize and sanitize tool_calls
    normalized_tool_calls: List[Dict[str, Any]] = []
    if tool_calls:
      for tc in tool_calls:
        if isinstance(tc, dict):
          tc_name = str(tc.get("name") or "unknown_tool")
          raw_args = tc.get("args") if "args" in tc else tc.get("parameters", {})
          sanitized_args = _sanitize_for_serialization(raw_args)
          tc_args = sanitized_args if isinstance(sanitized_args, dict) else {"input": sanitized_args}
          normalized_tool_calls.append({"name": tc_name, "args": tc_args})
        else:
          tc_name = getattr(tc, "name", None) or getattr(tc, "__name__", None) or "tool_call"
          normalized_tool_calls.append(
              {"name": str(tc_name), "args": {"raw": _sanitize_for_serialization(tc)}}
          )

    # Normalize and sanitize tool_outputs
    normalized_tool_outputs: List[Dict[str, Any]] = []
    if tool_outputs:
      for to in tool_outputs:
        if isinstance(to, dict):
          to_name = str(to.get("name") or "unknown_tool")
          raw_resp = to.get("output") if "output" in to else to.get("response", to)
          sanitized_resp = _sanitize_for_serialization(raw_resp)
          normalized_tool_outputs.append({"name": to_name, "output": sanitized_resp})
        else:
          to_name = getattr(to, "name", None) or getattr(to, "__name__", None) or "tool_output"
          sanitized_resp = _sanitize_for_serialization(to)
          normalized_tool_outputs.append({"name": str(to_name), "output": sanitized_resp})

    with self._lock:
      turn = SessionTurn(
          turn_id=str(uuid.uuid4())[:8],
          role=role,
          content=content_clean,
          tool_calls=normalized_tool_calls,
          tool_outputs=normalized_tool_outputs,
          state_snapshot=copy.deepcopy(self.state),
      )
      self.turns.append(turn)

    # Route event to VertexAiSessionService if active
    if self.session_service and self.adk_session:
      try:
        from google.adk.events import Event
        from google.genai import types

        parts = []
        if content_clean:
          parts.append(types.Part.from_text(text=content_clean))

        # Serialize tool_calls into FunctionCall parts
        for tc in normalized_tool_calls:
          tc_name = tc["name"]
          tc_args = tc["args"]
          try:
            parts.append(types.Part.from_function_call(name=tc_name, args=tc_args))
          except Exception:
            parts.append(types.Part.from_text(text=f"[Tool Call: {tc_name}({tc_args})]"))

        # Serialize tool_outputs into FunctionResponse parts
        for to in normalized_tool_outputs:
          to_name = to["name"]
          raw_out = to["output"]
          resp_dict = raw_out if isinstance(raw_out, dict) else {"output": raw_out}
          try:
            parts.append(types.Part.from_function_response(name=to_name, response=resp_dict))
          except Exception:
            parts.append(types.Part.from_text(text=f"[Tool Output {to_name}: {resp_dict}]"))

        if not parts:
          parts.append(types.Part.from_text(text=""))

        genai_role = "model" if role in ("assistant", "model") else role
        content_obj = types.Content(
            role=genai_role,
            parts=parts,
        )
        event = Event(
            author=role,
            content=content_obj,
            branch=self.branch_name,
        )
        _invoke_maybe_async(
            self.session_service.append_event,
            session=self.adk_session,
            event=event,
        )
      except Exception as e:
        logger.warning(
            "Failed to route turn event to VertexAiSessionService (%s). Kept in local transcript.",
            e,
        )

    return turn

  def rewind_to_turn(self, turn_id: str) -> bool:
    """Rolls back session turns to a specific turn ID (Replay / Rewind pattern)."""
    if not turn_id or not turn_id.strip():
      return False
    target_clean = turn_id.strip()

    with self._lock:
      idx = -1
      for i, t in enumerate(self.turns):
        if t.turn_id == target_clean:
          idx = i
          break
      if idx != -1:
        restored_snapshot = copy.deepcopy(self.turns[idx].state_snapshot)
        self.turns = self.turns[: idx + 1]
        self.state = restored_snapshot

        # Notify managed session backend of rewind trajectory change if active
        if self.session_service and self.adk_session:
          try:
            from google.adk.events import Event
            from google.genai import types

            rewind_event = Event(
                author="system",
                content=types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"[REWIND] Session trajectory reverted to turn {target_clean}")],
                ),
                branch=self.branch_name,
            )
            _invoke_maybe_async(
                self.session_service.append_event,
                session=self.adk_session,
                event=rewind_event,
            )
          except Exception as e:
            logger.warning("Failed to synchronize rewind event to VertexAiSessionService: %s", e)

        return True
    return False

  def branch(self, new_branch_name: str, from_turn_id: Optional[str] = None) -> "Session":
    """Creates an isolated branch of the current session trajectory, optionally from a specific turn."""
    if not new_branch_name or not new_branch_name.strip():
      raise ValueError("Branch name cannot be empty")

    branch_name_clean = new_branch_name.strip()

    with self._lock:
      if from_turn_id:
        target_id = from_turn_id.strip()
        idx = -1
        for i, t in enumerate(self.turns):
          if t.turn_id == target_id:
            idx = i
            break
        if idx == -1:
          raise ValueError(f"Turn ID '{from_turn_id}' not found in session '{self.session_id}'")
        target_turns = self.turns[: idx + 1]
        target_state = copy.deepcopy(self.turns[idx].state_snapshot)
      else:
        target_turns = self.turns
        target_state = copy.deepcopy(self.state)

      # Reconstruct turns to ensure deep isolation from parent mutations
      cloned_turns = [
          SessionTurn(
              turn_id=t.turn_id,
              role=t.role,
              content=t.content,
              tool_calls=copy.deepcopy(t.tool_calls),
              tool_outputs=copy.deepcopy(t.tool_outputs),
              timestamp=t.timestamp,
              state_snapshot=copy.deepcopy(t.state_snapshot),
          )
          for t in target_turns
      ]

    child = Session(
        session_id=f"{self.session_id}-branch-{branch_name_clean}",
        turns=cloned_turns,
        state=target_state,
        parent_session_id=self.session_id,
        branch_name=branch_name_clean,
        session_service=self.session_service,
        adk_session=self.adk_session,
        app_name=self.app_name,
        user_id=self.user_id,
    )
    return child


class SessionManager:
  """Dual-backend session manager supporting Local In-Memory & Vertex AI Sessions."""

  def __init__(
      self,
      use_vertex: bool = False,
      project_id: Optional[str] = None,
      location: Optional[str] = None,
      agent_engine_id: Optional[str] = None,
      session_service: Optional[Any] = None,
      app_name: str = "coding-harness",
      user_id: str = "default-user",
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
    self.app_name = app_name
    self.user_id = user_id
    self._sessions: Dict[str, Session] = {}
    self._lock = threading.RLock()

    self._managed_active = False
    self.vertex_session_service = None

    if use_vertex or session_service is not None:
      if session_service is not None:
        self.vertex_session_service = session_service
        self._managed_active = True
      else:
        try:
          from google.adk.sessions import VertexAiSessionService

          self.vertex_session_service = VertexAiSessionService(
              project=self.project_id,
              location=self.location,
              agent_engine_id=self.agent_engine_id,
          )
          self._managed_active = True
        except Exception as e:
          logger.warning(
              "Could not initialize VertexAiSessionService (%s). Falling back to local in-memory sessions.",
              e,
          )
          self._managed_active = False
          self.vertex_session_service = None

  @property
  def mode(self) -> str:
    """Returns 'managed' if Vertex AI Sessions backend is active, else 'local'."""
    return "managed" if self._managed_active else "local"

  @property
  def is_managed(self) -> bool:
    return self._managed_active

  @property
  def use_vertex(self) -> bool:
    return self._managed_active

  def get_or_create(self, session_id: Optional[str] = None) -> Session:
    """Retrieves an existing session or creates a new one in the active backend."""
    sid = session_id.strip() if (session_id and session_id.strip()) else str(uuid.uuid4())[:8]

    with self._lock:
      if sid in self._sessions:
        return self._sessions[sid]

      adk_session = None
      if self._managed_active and self.vertex_session_service:
        try:
          adk_session = _invoke_maybe_async(
              self.vertex_session_service.create_session,
              app_name=self.app_name,
              user_id=self.user_id,
              state={"harness_session_id": sid, "branch": "main"},
          )
        except Exception as e:
          logger.warning(
              "VertexAiSessionService.create_session failed (%s). Falling back to local session.",
              e,
          )

      sess = Session(
          session_id=sid,
          adk_session=adk_session,
          session_service=self.vertex_session_service if self._managed_active else None,
          app_name=self.app_name,
          user_id=self.user_id,
      )
      self._sessions[sid] = sess
      return sess

  def branch_session(
      self,
      session_id: str,
      new_branch_name: str,
      from_turn_id: Optional[str] = None,
  ) -> Session:
    """Branches an existing session, handling turn slicing, collision disambiguation, and ADK synchronization."""
    sid = session_id.strip() if session_id else ""
    if not sid:
      raise KeyError("Session ID cannot be empty")

    with self._lock:
      if sid not in self._sessions:
        raise KeyError(f"Session '{sid}' not found")

      parent_session = self._sessions[sid]
      child = parent_session.branch(new_branch_name=new_branch_name, from_turn_id=from_turn_id)

      # Disambiguate session ID on collision
      base_child_id = child.session_id
      disambiguated_id = base_child_id
      counter = 1
      while disambiguated_id in self._sessions:
        disambiguated_id = f"{base_child_id}-{counter}"
        counter += 1

      child.session_id = disambiguated_id

      # If managed mode is active, create dedicated ADK session for the branch
      if self._managed_active and self.vertex_session_service:
        try:
          adk_branch_session = _invoke_maybe_async(
              self.vertex_session_service.create_session,
              app_name=self.app_name,
              user_id=self.user_id,
              state={
                  "harness_session_id": disambiguated_id,
                  "branch": child.branch_name,
                  "parent_session_id": sid,
              },
          )
          child.adk_session = adk_branch_session
        except Exception as e:
          logger.warning("Failed to create managed session for branch (%s): fallback to local", e)

      self._sessions[disambiguated_id] = child
      return child

  def list_sessions(self) -> List[Dict[str, Any]]:
    return [
        {
            "session_id": s.session_id,
            "turn_count": len(s.turns),
            "branch_name": s.branch_name,
            "parent_session_id": s.parent_session_id,
            "mode": self.mode,
            "managed_id": s.adk_session.id if s.adk_session else None,
        }
        for s in self._sessions.values()
    ]

