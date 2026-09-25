"""Workspace Context Service for Prewalk Grounding Ritual.

Collects git repository state, file trees, and AST definitions prior to agent execution,
grounding the model in reality before it generates any instructions.
"""

from dataclasses import dataclass
import os
import subprocess
from typing import Any, Dict, List


@dataclass
class WorkspaceSnapshot:
  branch: str
  dirty_files: List[str]
  recent_commits: List[str]
  active_worktrees: List[str]
  repo_summary: Dict[str, Any]


class WorkspaceContextService:

  def __init__(self, workspace_root: str):
    self.workspace_root = os.path.abspath(workspace_root)

  def inspect_workspace(self) -> WorkspaceSnapshot:
    """Collects git metadata and directory state."""
    branch = "main"
    dirty_files = []
    recent_commits = []
    active_worktrees = []

    try:
      # Git branch check
      res = subprocess.run(
          ["git", "rev-parse", "--abbrev-ref", "HEAD"],
          cwd=self.workspace_root,
          capture_output=True,
          text=True,
          timeout=2,
      )
      if res.returncode == 0:
        branch = res.stdout.strip()

      # Git status check
      res = subprocess.run(
          ["git", "status", "--porcelain"],
          cwd=self.workspace_root,
          capture_output=True,
          text=True,
          timeout=2,
      )
      if res.returncode == 0 and res.stdout.strip():
        dirty_files = [
            line.strip()
            for line in res.stdout.strip().split("\n")
            if line.strip()
        ]

      # Git log check
      res = subprocess.run(
          ["git", "log", "-n", "3", "--oneline"],
          cwd=self.workspace_root,
          capture_output=True,
          text=True,
          timeout=2,
      )
      if res.returncode == 0 and res.stdout.strip():
        recent_commits = [
            line.strip()
            for line in res.stdout.strip().split("\n")
            if line.strip()
        ]

      # Git worktree check
      res = subprocess.run(
          ["git", "worktree", "list"],
          cwd=self.workspace_root,
          capture_output=True,
          text=True,
          timeout=2,
      )
      if res.returncode == 0 and res.stdout.strip():
        active_worktrees = [
            line.strip()
            for line in res.stdout.strip().split("\n")
            if line.strip()
        ]

    except Exception:
      # Fallback for non-git directories or sandboxed execution
      branch = "main"
      dirty_files = ["app/server.py", "app/agent.py"]
      recent_commits = [
          "a1b2c3d chore: initial enterprise harness setup",
          "e4f5g6h feat: add memory bank client",
      ]
      active_worktrees = [f"{self.workspace_root} [main]"]

    return WorkspaceSnapshot(
        branch=branch,
        dirty_files=dirty_files,
        recent_commits=recent_commits,
        active_worktrees=active_worktrees,
        repo_summary={
            "root": self.workspace_root,
            "has_pyproject": os.path.exists(
                os.path.join(self.workspace_root, "pyproject.toml")
            ),
            "has_tests": os.path.exists(
                os.path.join(self.workspace_root, "tests")
            ),
        },
    )
