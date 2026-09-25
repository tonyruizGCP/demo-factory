"""Harness State & Snapshot Registry for Repeatable ADK Agents.

Enables reproducible agent development and hill-climbing by capturing an immutable
record of the harness's original state (configuration, prompts, code hashes, git commits,
and baseline evaluation metrics) before experimental mutations are applied.

Provides:
1. `HarnessSnapshot`: Serializable, immutable state container.
2. `HarnessSnapshotManager`: Capture, diff, rollback, and verification workflows.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional

from app.config import HarnessConfig, get_config


def compute_dir_code_hash(directory: str, extensions: tuple = (".py", ".yaml", ".json")) -> str:
    """Computes a deterministic SHA256 signature across all source files."""
    hasher = hashlib.sha256()
    root_path = Path(directory)
    
    # Sort files deterministically
    sorted_files = sorted(
        [
            p for p in root_path.rglob("*")
            if p.is_file() and p.suffix in extensions and not any(part.startswith((".", "__pycache__", "venv")) for part in p.parts)
        ],
        key=lambda p: str(p.relative_to(root_path))
    )

    for file_path in sorted_files:
        rel_name = str(file_path.relative_to(root_path)).encode("utf-8")
        hasher.update(rel_name)
        try:
            with open(file_path, "rb") as f:
                hasher.update(f.read())
        except Exception:
            continue

    return hasher.hexdigest()


@dataclass
class HarnessSnapshot:
    """Immutable manifest representing the complete state of an ADK agent harness."""

    snapshot_id: str
    name: str
    created_at_utc: str
    git_commit: str
    git_branch: str
    is_git_dirty: bool
    dirty_patch: str
    code_hash: str
    config: Dict[str, Any]
    prompt_registry: Dict[str, str]
    active_tools: List[str]
    active_callbacks: List[str]
    evaluation_metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HarnessSnapshot:
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> HarnessSnapshot:
        return cls.from_dict(json.loads(json_str))


class HarnessSnapshotManager:
    """Manages baseline snapshots, candidate tracking, diffing, and rollbacks."""

    def __init__(self, workspace_root: str = ".", snapshot_dir: str = ".harness_snapshots"):
        self.workspace_root = os.path.abspath(workspace_root)
        self.snapshot_dir = Path(self.workspace_root) / snapshot_dir
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def capture_snapshot(
        self,
        name: str = "baseline_v1",
        evaluation_metrics: Optional[Dict[str, Any]] = None,
        custom_prompts: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HarnessSnapshot:
        """Captures the current state of the harness as a versioned snapshot."""
        now_iso = datetime.now(timezone.utc).isoformat()
        snapshot_id = f"{name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        # 1. Git state inspection
        git_commit = "unknown"
        git_branch = "unknown"
        is_dirty = False
        dirty_patch = ""

        try:
            res_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res_commit.returncode == 0:
                git_commit = res_commit.stdout.strip()

            res_branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res_branch.returncode == 0:
                git_branch = res_branch.stdout.strip()

            res_diff = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res_diff.returncode == 0 and res_diff.stdout.strip():
                is_dirty = True
                dirty_patch = res_diff.stdout
        except Exception:
            pass

        # 2. Code hash signature
        app_dir = os.path.join(self.workspace_root, "app")
        code_hash = compute_dir_code_hash(app_dir if os.path.exists(app_dir) else self.workspace_root)

        # 3. Config state
        cfg = get_config()
        config_dict = {
            "use_managed_services": cfg.use_managed_services,
            "use_managed_sessions": cfg.use_managed_sessions,
            "use_managed_memory_bank": cfg.use_managed_memory_bank,
            "project_id": cfg.project_id,
            "location": cfg.location,
            "agent_engine_id": cfg.agent_engine_id,
        }

        # 4. Prompt Registry
        prompts = custom_prompts or {
            "lead_agent_metaprompt": (
                "You are an expert enterprise coding orchestrator. You navigate repositories"
                " using in-process LSP, delegate refactoring tasks to isolated subagents,"
                " and verify syntax before committing."
            ),
            "refactor_subagent_prompt": (
                "You are an isolated refactoring specialist operating inside a Git worktree."
                " Apply semantic patches and verify AST syntax."
            ),
            "prewalk_guideline_policy": "Inject Vertex Memory Bank corporate conventions (top_k=5).",
        }

        # 5. Registered Tools & Callbacks
        active_tools = [
            "lsp_find_definition",
            "lsp_find_references",
            "lsp_get_diagnostics",
            "apply_semantic_patch",
            "create_worktree_sandbox",
            "cleanup_worktree_sandbox",
            "dap_run_pytest",
            "dap_evaluate_python_snippet",
        ]
        active_callbacks = [
            "prewalk_workspace_grounding",
            "post_tool_verification_hook",
        ]

        snapshot = HarnessSnapshot(
            snapshot_id=snapshot_id,
            name=name,
            created_at_utc=now_iso,
            git_commit=git_commit,
            git_branch=git_branch,
            is_git_dirty=is_dirty,
            dirty_patch=dirty_patch,
            code_hash=code_hash,
            config=config_dict,
            prompt_registry=prompts,
            active_tools=active_tools,
            active_callbacks=active_callbacks,
            evaluation_metrics=evaluation_metrics or {},
            metadata=metadata or {},
        )

        # Save to disk
        out_path = self.snapshot_dir / f"{name}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(snapshot.to_json())

        # Also save timestamped archive
        archive_path = self.snapshot_dir / f"{snapshot_id}.json"
        with open(archive_path, "w", encoding="utf-8") as f:
            f.write(snapshot.to_json())

        return snapshot

    def load_snapshot(self, name_or_id: str) -> Optional[HarnessSnapshot]:
        """Loads a snapshot by name or ID."""
        target_path = self.snapshot_dir / f"{name_or_id}.json"
        if not target_path.exists():
            # Check without .json
            target_path = self.snapshot_dir / name_or_id
            if not target_path.exists():
                return None

        with open(target_path, "r", encoding="utf-8") as f:
            return HarnessSnapshot.from_json(f.read())

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Lists all captured snapshots."""
        records = []
        for file in sorted(self.snapshot_dir.glob("*.json")):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    snap = json.load(f)
                    records.append({
                        "name": snap.get("name"),
                        "snapshot_id": snap.get("snapshot_id"),
                        "created_at_utc": snap.get("created_at_utc"),
                        "git_commit": snap.get("git_commit")[:7] if snap.get("git_commit") else "none",
                        "code_hash": snap.get("code_hash")[:8] if snap.get("code_hash") else "none",
                        "pass_rate": snap.get("evaluation_metrics", {}).get("pass_rate", "N/A"),
                        "file": str(file),
                    })
            except Exception:
                continue
        return records

    def diff_snapshots(self, base_name: str, candidate_name: str) -> Dict[str, Any]:
        """Generates a structural diff between a baseline and candidate snapshot."""
        base = self.load_snapshot(base_name)
        cand = self.load_snapshot(candidate_name)

        if not base or not cand:
            raise FileNotFoundError(f"Snapshots '{base_name}' or '{candidate_name}' could not be loaded.")

        diff_res = {
            "baseline": {"name": base.name, "id": base.snapshot_id, "commit": base.git_commit[:7]},
            "candidate": {"name": cand.name, "id": cand.snapshot_id, "commit": cand.git_commit[:7]},
            "code_changed": base.code_hash != cand.code_hash,
            "config_changes": {},
            "prompt_changes": {},
            "metric_delta": {},
        }

        # Compare Config
        for k, v in cand.config.items():
            if base.config.get(k) != v:
                diff_res["config_changes"][k] = {"before": base.config.get(k), "after": v}

        # Compare Prompts
        for k, v in cand.prompt_registry.items():
            if base.prompt_registry.get(k) != v:
                diff_res["prompt_changes"][k] = {
                    "before": base.prompt_registry.get(k),
                    "after": v,
                }

        # Compare Metrics
        b_metrics = base.evaluation_metrics
        c_metrics = cand.evaluation_metrics
        if b_metrics and c_metrics:
            for k in set(b_metrics.keys()).union(c_metrics.keys()):
                diff_res["metric_delta"][k] = {
                    "baseline": b_metrics.get(k),
                    "candidate": c_metrics.get(k),
                }

        return diff_res
