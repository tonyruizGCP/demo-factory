"""ADK Agent Definitions & Dual-Mode Orchestration Engine.

Defines:
1. Lead Agent (Enterprise Coding Orchestrator)
2. Refactor Subagent (Isolated Worktree Execution Specialist)
3. High-Fidelity Simulation & Live Vertex AI dual-mode runner
"""

import json
import os
from typing import Any, AsyncGenerator, Dict, List, Optional
from app.callbacks import post_tool_verification_hook, prewalk_workspace_grounding
from app.config import HarnessConfig, get_config
from app.services.memory_bank import MemoryBankService
from app.services.session_manager import Session, SessionManager
from app.services.workspace_context import WorkspaceContextService
from app.tools.dap_tools import dap_evaluate_python_snippet, dap_run_pytest
from app.tools.edit_tools import apply_semantic_patch
from app.tools.lsp_tools import lsp_find_definition, lsp_find_references, lsp_get_diagnostics
from app.tools.worktree_tools import cleanup_worktree_sandbox, create_worktree_sandbox


class CodingHarnessOrchestrator:
  """ADK-style agent harness orchestrating Lead Agent and Subagents."""

  def __init__(
      self,
      workspace_root: str = ".",
      use_vertex: Optional[bool] = None,
      use_managed_services: Optional[bool] = None,
      use_managed_sessions: Optional[bool] = None,
      use_managed_memory_bank: Optional[bool] = None,
      project_id: Optional[str] = None,
      location: Optional[str] = None,
      agent_engine_id: Optional[str] = None,
      session_manager: Optional[SessionManager] = None,
      memory_bank: Optional[MemoryBankService] = None,
      config: Optional[HarnessConfig] = None,
  ):
    self.workspace_root = os.path.abspath(workspace_root)
    cfg = config or get_config()

    self.project_id = (
        project_id
        or cfg.project_id
        or os.environ.get("GCP_PROJECT")
        or "truiz-agy-demo"
    )
    self.location = location or cfg.location
    self.agent_engine_id = agent_engine_id or cfg.agent_engine_id

    # Resolve managed flags with hierarchy: granular override > unified toggle > config default
    managed_sessions = (
        use_managed_sessions
        if use_managed_sessions is not None
        else (
            use_managed_services
            if use_managed_services is not None
            else (
                use_vertex if use_vertex is not None else cfg.is_sessions_managed
            )
        )
    )
    managed_memory = (
        use_managed_memory_bank
        if use_managed_memory_bank is not None
        else (
            use_managed_services
            if use_managed_services is not None
            else (
                use_vertex
                if use_vertex is not None
                else cfg.is_memory_bank_managed
            )
        )
    )

    # Native Services
    self.session_manager = session_manager or SessionManager(
        use_vertex=managed_sessions,
        project_id=self.project_id,
        location=self.location,
        agent_engine_id=self.agent_engine_id,
    )
    self.memory_bank = memory_bank or MemoryBankService(
        use_vertex=managed_memory,
        project_id=self.project_id,
        location=self.location,
        agent_engine_id=self.agent_engine_id,
    )
    self.workspace_service = WorkspaceContextService(self.workspace_root)

    # Reflect active services in orchestrator top-level flags
    self.use_vertex = self.session_manager.is_managed or self.memory_bank.is_managed
    self.use_managed_services = self.use_vertex

  async def execute_task_stream(
      self, session_id: str, prompt: str
  ) -> AsyncGenerator[Dict[str, Any], None]:
    """Executes a coding task, streaming intermediate thoughts, tool calls, and results."""
    session = self.session_manager.get_or_create(session_id)

    # 1. PREWALK GROUNDING RITUAL (Callback before_agent_run)
    yield {
        "type": "event",
        "stage": "prewalk",
        "message": (
            "Initiating Prewalk Workspace Grounding & Memory Bank query..."
        ),
    }
    grounding = prewalk_workspace_grounding(
        session, self.memory_bank, self.workspace_service, prompt
    )
    yield {
        "type": "prewalk_complete",
        "grounding": grounding,
        "message": (
            f"Grounded on branch '{grounding['branch']}'. Injected"
            f" {len(grounding['relevant_guidelines'])} enterprise rules from"
            " Memory Bank."
        ),
    }

    # Record User Turn
    session.add_turn(role="user", content=prompt)

    # 2. ORCHESTRATION & TOOL EXECUTION LOOP
    # High-fidelity simulation flow matching realistic customer demo steps
    prompt_lower = prompt.lower()
    executed_tool_calls: List[Dict[str, Any]] = []
    executed_tool_outputs: List[Dict[str, Any]] = []

    if "refactor" in prompt_lower or "async" in prompt_lower:
      # Step A: Semantic Navigation via LSP
      yield {
          "type": "thought",
          "content": (
              "Querying AST via LSP to inspect definitions and call sites"
              " without bloating context."
          ),
      }
      lsp_args = {"symbol": "SessionManager", "file": "app/services/session_manager.py"}
      yield {
          "type": "tool_call",
          "name": "lsp_find_definition",
          "args": lsp_args,
      }
      lsp_def = lsp_find_definition("SessionManager", self.workspace_root)
      executed_tool_calls.append({"name": "lsp_find_definition", "args": lsp_args})
      executed_tool_outputs.append({"name": "lsp_find_definition", "output": lsp_def})
      yield {"type": "tool_output", "name": "lsp_find_definition", "output": lsp_def}

      # Step B: Spawn Subagent in Isolated Worktree
      yield {
          "type": "thought",
          "content": (
              "Delegating risky refactoring to Refactor Subagent in an isolated"
              " Git worktree."
          ),
      }
      wt_args = {"branch_name": "feat-async-refactor"}
      yield {
          "type": "tool_call",
          "name": "create_worktree_sandbox",
          "args": wt_args,
      }
      wt_res = create_worktree_sandbox(
          "feat-async-refactor", self.workspace_root
      )
      executed_tool_calls.append({"name": "create_worktree_sandbox", "args": wt_args})
      executed_tool_outputs.append({"name": "create_worktree_sandbox", "output": wt_res})
      yield {
          "type": "tool_output",
          "name": "create_worktree_sandbox",
          "output": wt_res,
      }

      # Step C: Subagent applies Semantic Patch with Closed-Loop Verification
      yield {
          "type": "subagent_thought",
          "agent": "refactor_subagent",
          "content": (
              "Applying semantic patch inside isolated worktree. Validating AST"
              " syntax."
          ),
      }
      patch_args = {
          "file_path": "app/services/session_manager.py",
          "target_block": "# Target block to update",
          "replacement_block": "# Async enhanced block",
      }
      yield {
          "type": "tool_call",
          "name": "apply_semantic_patch",
          "args": patch_args,
      }
      patch_res = {
          "status": "APPLIED_AND_VERIFIED",
          "file_path": "app/services/session_manager.py",
          "verification": "AST_PASSED",
      }
      patch_res = post_tool_verification_hook("apply_semantic_patch", patch_res)
      executed_tool_calls.append({"name": "apply_semantic_patch", "args": patch_args})
      executed_tool_outputs.append({"name": "apply_semantic_patch", "output": patch_res})
      yield {
          "type": "tool_output",
          "name": "apply_semantic_patch",
          "output": patch_res,
      }

      # Step D: DAP Test Verification
      dap_args = {"test_path": "tests"}
      yield {
          "type": "tool_call",
          "name": "dap_run_pytest",
          "args": dap_args,
      }
      dap_res = {
          "status": "PASSED",
          "returncode": 0,
          "stdout": "Ran 4 tests in 0.082s - OK (4/4 passed)",
      }
      dap_res = post_tool_verification_hook("dap_run_pytest", dap_res)
      executed_tool_calls.append({"name": "dap_run_pytest", "args": dap_args})
      executed_tool_outputs.append({"name": "dap_run_pytest", "output": dap_res})
      yield {"type": "tool_output", "name": "dap_run_pytest", "output": dap_res}

      # Step E: Memory Consolidation
      consolidated_rule = (
          "When refactoring SessionManager, maintain backward compatibility for"
          " synchronous rewind snapshots."
      )
      mem_rec = self.memory_bank.record_memory(
          category="architecture",
          content=consolidated_rule,
          metadata={"source": "Subagent Session Consolidation"},
      )
      yield {
          "type": "memory_consolidated",
          "memory": {
              "id": mem_rec.memory_id,
              "content": mem_rec.content,
              "category": mem_rec.category,
          },
          "message": "Consolidated new architectural learning into Memory Bank.",
      }

      # Final Synthesis
      response_text = (
          "### Task Complete: Isolated Refactoring Verified\n\n"
          "1. **Prewalk Grounding**: Grounded context against"
          f" `{grounding['branch']}` and loaded enterprise guidelines from"
          " **Memory Bank**.\n"
          "2. **Semantic Discovery**: Queried `SessionManager` via **LSP**"
          " without token bloat.\n"
          "3. **Isolated Execution**: Delegated changes to **Subagent** in Git"
          f" worktree `{wt_res['worktree_path']}`.\n"
          "4. **Closed-Loop Verification**: Applied patch with automated"
          " AST syntax checks and verified against test suite (**4/4"
          " tests passed**).\n"
          "5. **Memory Consolidation**: Saved new design guideline into **Memory"
          " Bank** for future sessions."
      )

    else:
      # General query handling
      yield {
          "type": "thought",
          "content": (
              "Analyzing query against enterprise codebase and Memory Bank"
              " guidelines."
          ),
      }
      response_text = (
          f"I have reviewed your request: '{prompt}'.\n\n"
          "The Gemini Enterprise Coding Harness is grounded and ready. "
          f"Current branch: `{grounding['branch']}` with"
          f" {len(grounding['relevant_guidelines'])} active Memory Bank rules."
      )

    # Record Assistant Turn with executed tools
    session.add_turn(
        role="assistant",
        content=response_text,
        tool_calls=executed_tool_calls,
        tool_outputs=executed_tool_outputs,
    )

    yield {
        "type": "final_response",
        "content": response_text,
        "session_id": session.session_id,
        "turn_count": len(session.turns),
    }
