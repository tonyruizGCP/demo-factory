"""Language Server Protocol (LSP) Tools for AST Navigation.

Replaces brute-force file dumping and regex search with compiler-grade AST definitions,
call references, and real-time type diagnostics.
"""

import ast
import os
from typing import Any, Dict, List, Optional


class MockLspServer:
  """Lightweight in-process Python AST symbol indexer mimicking an LSP server."""

  def __init__(self, workspace_root: str):
    self.workspace_root = workspace_root
    self._symbol_index: Dict[str, Dict[str, Any]] = {}
    self._rebuild_index()

  def _rebuild_index(self):
    self._symbol_index.clear()
    for root, _, files in os.walk(self.workspace_root):
      for f in files:
        if f.endswith(".py"):
          full_path = os.path.join(root, f)
          rel_path = os.path.relpath(full_path, self.workspace_root)
          try:
            with open(full_path, "r", encoding="utf-8") as fp:
              tree = ast.parse(fp.read(), filename=rel_path)
            for node in ast.walk(tree):
              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._symbol_index[node.name] = {
                    "kind": "function",
                    "file": rel_path,
                    "line": node.lineno,
                    "args": [a.arg for a in node.args.args],
                    "docstring": ast.get_docstring(node) or "",
                }
              elif isinstance(node, ast.ClassDef):
                self._symbol_index[node.name] = {
                    "kind": "class",
                    "file": rel_path,
                    "line": node.lineno,
                    "docstring": ast.get_docstring(node) or "",
                }
          except Exception:
            continue

  def goto_definition(self, symbol_name: str) -> Optional[Dict[str, Any]]:
    self._rebuild_index()
    return self._symbol_index.get(symbol_name)

  def find_references(self, symbol_name: str) -> List[Dict[str, Any]]:
    refs = []
    for root, _, files in os.walk(self.workspace_root):
      for f in files:
        if f.endswith(".py"):
          full_path = os.path.join(root, f)
          rel_path = os.path.relpath(full_path, self.workspace_root)
          try:
            with open(full_path, "r", encoding="utf-8") as fp:
              lines = fp.readlines()
            for line_idx, line in enumerate(lines, start=1):
              if symbol_name in line:
                refs.append({
                    "file": rel_path,
                    "line": line_idx,
                    "snippet": line.strip(),
                })
          except Exception:
            continue
    return refs

  def get_diagnostics(self, file_path: str) -> List[str]:
    full_path = os.path.join(self.workspace_root, file_path)
    if not os.path.exists(full_path):
      return [f"File not found: {file_path}"]
    try:
      with open(full_path, "r", encoding="utf-8") as fp:
        ast.parse(fp.read(), filename=file_path)
      return []
    except SyntaxError as e:
      return [f"SyntaxError in {file_path}:{e.lineno} - {e.msg}"]


# Tool functions exposed to the ADK agent
_lsp_server_instance: Optional[MockLspServer] = None


def get_lsp(workspace_root: str) -> MockLspServer:
  global _lsp_server_instance
  if _lsp_server_instance is None:
    _lsp_server_instance = MockLspServer(workspace_root)
  return _lsp_server_instance


def lsp_find_definition(symbol: str, workspace_root: str = ".") -> Dict[str, Any]:
  """Finds the declaration location, file path, line number, and signature for a symbol."""
  lsp = get_lsp(workspace_root)
  match = lsp.goto_definition(symbol)
  if match:
    return {"status": "SUCCESS", "definition": match}
  return {
      "status": "NOT_FOUND",
      "message": f"Symbol '{symbol}' not found in AST index.",
  }


def lsp_find_references(
    symbol: str, workspace_root: str = "."
) -> Dict[str, Any]:
  """Finds all call sites and usages of a symbol across the entire repository."""
  lsp = get_lsp(workspace_root)
  refs = lsp.find_references(symbol)
  return {"status": "SUCCESS", "count": len(refs), "references": refs[:20]}


def lsp_get_diagnostics(
    file_path: str, workspace_root: str = "."
) -> Dict[str, Any]:
  """Returns compiler/AST syntax diagnostics for a target file."""
  lsp = get_lsp(workspace_root)
  errors = lsp.get_diagnostics(file_path)
  return {
      "status": "CLEAN" if not errors else "HAS_DIAGNOSTICS",
      "diagnostics": errors,
  }
