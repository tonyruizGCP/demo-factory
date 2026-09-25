"""ADK Lifecycle Callbacks for Gemini Enterprise Coding Harness.

Implements:
1. `before_agent_run`: Prewalk Workspace Grounding & Memory Bank Injection
2. `after_tool_run`: Closed-Loop Post-Edit Verification & Auto-Repair Signals
"""

from typing import Any, Dict
from app.services.memory_bank import MemoryBankService
from app.services.session_manager import Session
from app.services.workspace_context import WorkspaceContextService


def prewalk_workspace_grounding(
    session: Session,
    memory_bank: MemoryBankService,
    workspace_service: WorkspaceContextService,
    user_prompt: str,
) -> Dict[str, Any]:
  """Executes the pre-execution grounding ritual.

  Inspects the workspace and injects long-term enterprise memories directly into
  the session state before the agent reasons or acts.
  """
  # 1. Fetch relevant enterprise memories from Memory Bank
  relevant_memories = memory_bank.query_memories(user_prompt, top_k=3)

  # 2. Inspect workspace Git & file tree state
  snapshot = workspace_service.inspect_workspace()

  # 3. Store in session state
  grounding_payload = {
      "branch": snapshot.branch,
      "dirty_files": snapshot.dirty_files,
      "recent_commits": snapshot.recent_commits,
      "active_worktrees": snapshot.active_worktrees,
      "relevant_guidelines": [
          f"[{m.category.upper()}] {m.content}" for m in relevant_memories
      ],
  }
  session.state["workspace_grounding"] = grounding_payload
  return grounding_payload


def post_tool_verification_hook(tool_name: str, tool_output: Dict[str, Any]) -> Dict[str, Any]:
  """Closed-loop validation interceptor.

  Inspects tool execution outcomes and enriches the response with automated repair hints
  if syntax or test failures are detected.
  """
  if tool_name == "apply_semantic_patch":
    if tool_output.get("status") == "VERIFICATION_FAILED":
      tool_output["harness_action"] = "HALT_AND_REPAIR"
      tool_output["instruction_for_agent"] = (
          "Your patch introduced syntax errors. Review the repair_hint and"
          " re-apply the corrected patch immediately."
      )
    elif tool_output.get("status") == "APPLIED_AND_VERIFIED":
      tool_output["harness_action"] = "PROCEED"
      tool_output["instruction_for_agent"] = (
          "Patch passed AST validation. You may proceed with testing or commit."
      )

  elif tool_name == "dap_run_pytest":
    if tool_output.get("status") == "FAILED":
      tool_output["harness_action"] = "DIAGNOSE_FAILURE"
      tool_output["instruction_for_agent"] = (
          "Unit tests failed. Inspect stderr/stdout and isolate the root cause."
      )

  return tool_output
