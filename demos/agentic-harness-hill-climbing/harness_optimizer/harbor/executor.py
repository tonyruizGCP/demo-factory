"""Parallel batch trial execution engine."""

from __future__ import annotations

import concurrent.futures
from typing import Any, List, Optional

from harness_optimizer.harbor.sandbox import BaseSandbox, InMemoryMockHarness
from harness_optimizer.harbor.telemetry import TokenSpend, TrialTelemetry


class ConcurrentBatchExecutor:
    """Thread-safe batch executor coordinating parallel sandbox evaluations."""

    def __init__(
        self,
        sandbox: Optional[BaseSandbox] = None,
        max_workers: int = 4,
        **kwargs: Any,
    ) -> None:
        self.sandbox = sandbox or InMemoryMockHarness()
        self.max_workers = max(1, int(max_workers))
        self.kwargs = kwargs

    def execute_batch(
        self,
        tasks: List[Any],
        candidate: Any,
    ) -> List[TrialTelemetry]:
        """Execute a batch of evaluation tasks concurrently preserving input ordering."""
        if not tasks:
            return []
        if len(tasks) == 1:
            return [self._execute_single_trial(tasks[0], candidate)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = [pool.submit(self._execute_single_trial, task, candidate) for task in tasks]
            results = [f.result() for f in futures]
        return results

    def _execute_single_trial(self, task: Any, candidate: Any) -> TrialTelemetry:
        try:
            return self.sandbox.execute_trial(task, candidate)
        except Exception as exc:
            task_id = getattr(task, "task_id", None) or (
                task.get("task_id") if isinstance(task, dict) else "task_error"
            )
            cand_id = getattr(candidate, "candidate_id", None) or (
                candidate if isinstance(candidate, str) else "cand_error"
            )
            task_meta = dict(
                getattr(task, "metadata", {}) or (task.get("metadata", {}) if isinstance(task, dict) else {})
            )
            return TrialTelemetry(
                task_id=task_id,
                candidate_id=cand_id,
                passed=False,
                exit_code=1,
                latency_ms=0.0,
                token_spend=TokenSpend(),
                raw_error_message=f"Trial execution error: {exc}",
                metadata=task_meta,
            )


# Dual naming support for compatibility
BatchExecutor = ConcurrentBatchExecutor
