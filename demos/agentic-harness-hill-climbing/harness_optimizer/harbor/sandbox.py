"""Sandbox environments for executing agent trials (Mock and Subprocess)."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from harness_optimizer.harbor.config import SandboxConfig
from harness_optimizer.harbor.telemetry import TokenSpend, TraceSpan, TrialTelemetry

DEFAULT_ARCHETYPES = [
    "SyntaxError: invalid syntax in ast.parse() unexpected token",
    "TimeoutError: Execution watchdog timed out after deadline",
    "AssertionError: Unit test assertion failed: expected 42 but got 0",
    "RuntimeError: CUDA out of memory or tensor dimension mismatch",
    "KeyError: 'target_column' missing in intermediate dataframe",
    "MemoryError: Context length 65536 exceeded in attention block at 0x7f8a1c3d",
]


class AgentCandidate(BaseModel):
    """Candidate agent implementation representation under evaluation."""

    model_config = ConfigDict(extra="allow")

    candidate_id: str = Field(..., description="Unique identifier for the agent candidate")
    prompt_template: str = Field(default="", description="Optimization prompt template")
    system_prompt: Optional[str] = Field(default=None, description="System instructions")
    temperature: float = Field(default=0.0, ge=0.0, description="Sampling temperature")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary candidate metadata")


class BaseSandbox(ABC):
    """Abstract base class defining the execution interface for trial sandboxes."""

    @abstractmethod
    def execute_trial(self, task: Any, candidate: Any) -> TrialTelemetry:
        """Execute an individual trial and return structured telemetry."""
        pass


class InMemoryMockHarness(BaseSandbox):
    """Deterministic, thread-safe in-memory mock execution harness."""

    def __init__(
        self,
        failure_rate: float = 0.0,
        seed: Optional[int] = 42,
        error_archetypes: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        self.failure_rate = float(failure_rate)
        self.seed = seed if seed is not None else 42
        self.error_archetypes = error_archetypes if error_archetypes is not None else list(DEFAULT_ARCHETYPES)
        self._task_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
        self.kwargs = kwargs

    def execute_trial(self, task: Any, candidate: Any) -> TrialTelemetry:
        task_id = getattr(task, "task_id", None) or (
            task.get("task_id") if isinstance(task, dict) else "task_mock"
        )
        cand_id = getattr(candidate, "candidate_id", None) or (
            candidate if isinstance(candidate, str) else "cand_mock"
        )
        task_meta = dict(
            getattr(task, "metadata", {}) or (task.get("metadata", {}) if isinstance(task, dict) else {})
        )

        with self._lock:
            count = self._task_counts[task_id]
            self._task_counts[task_id] += 1

        if self.failure_rate <= 0.0:
            passed = True
        elif self.failure_rate >= 1.0:
            passed = False
        else:
            seed_key = f"{self.seed}:{task_id}:{count}".encode("utf-8")
            digest = hashlib.sha256(seed_key).digest()
            roll = int.from_bytes(digest[:8], "big") / (2**64)
            passed = bool(roll >= self.failure_rate)

        if passed:
            exit_code = 0
            raw_error = None
            latency_ms = 15.0
        else:
            exit_code = 1
            if self.error_archetypes:
                seed_key = f"{self.seed}:{task_id}:{count}:err".encode("utf-8")
                idx = int.from_bytes(hashlib.sha256(seed_key).digest()[:4], "big") % len(self.error_archetypes)
                raw_error = self.error_archetypes[idx]
            else:
                raw_error = "MockTrialError: Synthetic execution failure"
            latency_ms = 45.0

        spans = [
            TraceSpan(
                name="mock_execution",
                duration_ms=latency_ms,
                status="OK" if passed else "ERROR",
                attributes={"exit_code": exit_code},
            )
        ]
        token_spend = TokenSpend(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        return TrialTelemetry(
            task_id=task_id,
            candidate_id=cand_id,
            passed=passed,
            exit_code=exit_code,
            latency_ms=latency_ms,
            token_spend=token_spend,
            trace_logs=spans,
            raw_error_message=raw_error,
            metadata=task_meta,
        )


class SubprocessSandbox(BaseSandbox):
    """Subprocess sandbox executing commands in ephemeral isolated directories with watchdog timeouts."""

    def __init__(self, config: Optional[SandboxConfig] = None) -> None:
        self.config = config or SandboxConfig()

    def execute_trial(self, task: Any, candidate: Any) -> TrialTelemetry:
        task_id = getattr(task, "task_id", None) or (
            task.get("task_id") if isinstance(task, dict) else "task_subproc"
        )
        cand_id = getattr(candidate, "candidate_id", None) or (
            candidate if isinstance(candidate, str) else "cand_subproc"
        )
        task_meta = dict(
            getattr(task, "metadata", {}) or (task.get("metadata", {}) if isinstance(task, dict) else {})
        )

        vspec = getattr(task, "verification", None) or (
            task.get("verification") if isinstance(task, dict) else None
        )
        command = None
        task_timeout = None
        expected_exit = 0
        v_env: Dict[str, str] = {}

        if vspec is not None:
            command = getattr(vspec, "command", None) or (
                vspec.get("command") if isinstance(vspec, dict) else None
            )
            task_timeout = getattr(vspec, "timeout_seconds", None) or getattr(vspec, "timeout_sec", None)
            if task_timeout is None and isinstance(vspec, dict):
                task_timeout = vspec.get("timeout_seconds") or vspec.get("timeout_sec")
            expected_exit = getattr(vspec, "expected_exit_code", 0) if hasattr(vspec, "expected_exit_code") else (
                vspec.get("expected_exit_code", 0) if isinstance(vspec, dict) else 0
            )
            v_env = getattr(vspec, "environment_variables", {}) or (
                vspec.get("environment_variables", {}) if isinstance(vspec, dict) else {}
            )
        elif isinstance(task, dict) and "command" in task:
            command = task["command"]
            task_timeout = task.get("timeout_seconds") or task.get("timeout_sec") or task.get("timeout")

        config_timeout = self.config.timeout_sec or self.config.timeout_seconds or 30.0
        effective_timeout = config_timeout
        if task_timeout is not None:
            effective_timeout = min(config_timeout, float(task_timeout))

        use_temp = False
        temp_dir_obj = None
        if self.config.work_dir:
            if not os.path.isdir(self.config.work_dir):
                return TrialTelemetry(
                    task_id=task_id,
                    candidate_id=cand_id,
                    passed=False,
                    exit_code=1,
                    latency_ms=0.0,
                    token_spend=TokenSpend(),
                    raw_error_message=f"Working directory does not exist: {self.config.work_dir}",
                    metadata=task_meta,
                )
            target_dir = self.config.work_dir
        else:
            temp_dir_obj = tempfile.TemporaryDirectory()
            target_dir = temp_dir_obj.name
            use_temp = True

        env = os.environ.copy()
        env.update(self.config.env_vars)
        env.update(v_env)

        cmd = command if command else "true"
        t0 = time.perf_counter()
        passed = False
        exit_code = 1
        raw_error = None

        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=target_dir,
                env=env,
                capture_output=True,
                timeout=effective_timeout,
            )
            duration_ms = max(0.01, (time.perf_counter() - t0) * 1000.0)
            exit_code = proc.returncode
            stdout_str = proc.stdout.decode("utf-8", errors="replace")
            stderr_str = proc.stderr.decode("utf-8", errors="replace")
            passed = bool(exit_code == expected_exit)
            if not passed:
                raw_error = stderr_str.strip() or stdout_str.strip() or f"Process exited with status code {exit_code}"
        except subprocess.TimeoutExpired:
            duration_ms = max(0.01, (time.perf_counter() - t0) * 1000.0)
            exit_code = -9
            passed = False
            raw_error = f"Process watchdog timed out after {effective_timeout} seconds"
        except Exception as exc:
            duration_ms = max(0.01, (time.perf_counter() - t0) * 1000.0)
            exit_code = 1
            passed = False
            raw_error = f"Subprocess execution failed: {exc}"
        finally:
            if use_temp and self.config.cleanup and temp_dir_obj is not None:
                try:
                    temp_dir_obj.cleanup()
                except Exception:
                    pass

        spans = [
            TraceSpan(
                name="subprocess_execution",
                duration_ms=duration_ms,
                status="OK" if passed else "ERROR",
                attributes={"exit_code": exit_code, "command": cmd},
            )
        ]

        return TrialTelemetry(
            task_id=task_id,
            candidate_id=cand_id,
            passed=passed,
            exit_code=exit_code,
            latency_ms=duration_ms,
            token_spend=TokenSpend(),
            trace_logs=spans,
            raw_error_message=raw_error,
            metadata=task_meta,
        )
