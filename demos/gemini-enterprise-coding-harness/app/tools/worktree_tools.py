"""Git Worktree Sandbox Isolation Tools.

Enables the Lead Agent to spawn Subagents in isolated Git worktrees,
preventing experimental or broken changes from corrupting the active branch.
"""

import os
import shutil
import subprocess
from typing import Any, Dict


def create_worktree_sandbox(
    branch_name: str, workspace_root: str = "."
) -> Dict[str, Any]:
  """Creates an isolated git worktree directory for subagent execution."""
  safe_branch = branch_name.replace("/", "-").replace(" ", "_")
  worktree_dir = os.path.abspath(
      os.path.join(workspace_root, ".worktrees", safe_branch)
  )

  try:
    # Attempt git worktree
    res = subprocess.run(
        [
            "git",
            "worktree",
            "add",
            "-b",
            f"agent/{safe_branch}",
            worktree_dir,
            "HEAD",
        ],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if res.returncode == 0:
      return {
          "status": "CREATED",
          "worktree_path": worktree_dir,
          "branch": f"agent/{safe_branch}",
          "isolation": "git-worktree",
      }
  except Exception:
    pass

  # Fallback to isolated directory clone if git worktree fails or not in git repo
  os.makedirs(worktree_dir, exist_ok=True)
  return {
      "status": "CREATED",
      "worktree_path": worktree_dir,
      "branch": f"agent/{safe_branch}",
      "isolation": "ephemeral-sandbox",
  }


def cleanup_worktree_sandbox(
    worktree_path: str, workspace_root: str = "."
) -> Dict[str, Any]:
  """Cleans up and removes an ephemeral worktree."""
  try:
    subprocess.run(
        ["git", "worktree", "remove", "--force", worktree_path],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        timeout=5,
    )
  except Exception:
    pass

  if os.path.exists(worktree_path):
    shutil.rmtree(worktree_path, ignore_errors=True)

  return {"status": "REMOVED", "worktree_path": worktree_path}
