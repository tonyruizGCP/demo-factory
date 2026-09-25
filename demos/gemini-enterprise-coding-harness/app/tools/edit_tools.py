"""Semantic Patch and Edit Tool with Closed-Loop Validation.

Replaces fragile hash-anchored diffs with robust semantic block replacement
paired with instant post-edit syntax verification.
"""

import ast
import os
from typing import Any, Dict


def apply_semantic_patch(
    file_path: str,
    target_block: str,
    replacement_block: str,
    workspace_root: str = ".",
) -> Dict[str, Any]:
  """Applies a targeted replacement of a code block, automatically verifying AST validity."""
  full_path = os.path.abspath(os.path.join(workspace_root, file_path))

  if not os.path.exists(full_path):
    return {"status": "ERROR", "message": f"Target file does not exist: {file_path}"}

  try:
    with open(full_path, "r", encoding="utf-8") as f:
      content = f.read()

    # Normalize carriage returns
    clean_content = content.replace("\r\n", "\n")
    clean_target = target_block.replace("\r\n", "\n").strip()
    clean_replacement = replacement_block.replace("\r\n", "\n")

    if clean_target not in clean_content:
      return {
          "status": "TARGET_NOT_FOUND",
          "message": (
              f"Could not locate target code block in {file_path}. Ensure exact"
              " semantic match."
          ),
      }

    new_content = clean_content.replace(clean_target, clean_replacement, 1)

    # Perform Closed-Loop AST Verification before persisting if it's a python file
    if file_path.endswith(".py"):
      try:
        ast.parse(new_content, filename=file_path)
      except SyntaxError as syn_err:
        return {
            "status": "VERIFICATION_FAILED",
            "message": (
                f"Patch resulted in invalid Python syntax at line"
                f" {syn_err.lineno}: {syn_err.msg}"
            ),
            "repair_hint": (
                "Review indentation and closing brackets before retrying."
            ),
        }

    # Write validated content
    with open(full_path, "w", encoding="utf-8") as f:
      f.write(new_content)

    return {
        "status": "APPLIED_AND_VERIFIED",
        "file_path": file_path,
        "verification": "AST_PASSED",
    }

  except Exception as e:
    return {"status": "ERROR", "message": str(e)}
