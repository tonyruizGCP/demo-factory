"""Debug Adapter Protocol (DAP) & Execution Sandbox Tools.

Allows the agent to execute isolated tests, capture runtime tracebacks,
and evaluate state without guessing.
"""

import subprocess
import sys
from typing import Any, Dict


def dap_run_pytest(
    test_path: str = "tests", workspace_root: str = "."
) -> Dict[str, Any]:
  """Runs pytest or unit tests within the sandbox, capturing output and exit codes."""
  try:
    res = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", test_path],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return {
        "status": "PASSED" if res.returncode == 0 else "FAILED",
        "returncode": res.returncode,
        "stdout": res.stdout[-2000:],
        "stderr": res.stderr[-2000:],
    }
  except Exception as e:
    return {"status": "ERROR", "message": str(e)}


def dap_evaluate_python_snippet(code_snippet: str) -> Dict[str, Any]:
  """Executes an isolated Python expression or verification snippet in a scratchpad."""
  local_scope = {}
  try:
    # Safe evaluation of deterministic expressions
    exec(code_snippet, {}, local_scope)
    return {
        "status": "SUCCESS",
        "scope_variables": {
            k: str(v) for k, v in local_scope.items() if not k.startswith("_")
        },
    }
  except Exception as e:
    return {"status": "RUNTIME_EXCEPTION", "error": f"{type(e).__name__}: {e}"}
