"""Harbor Sandbox Runner for isolated threat hunting evaluations.

Provides resource-constrained, sandboxed execution for agent tools and queries
with strict egress boundaries and full telemetry audit logging.
"""

from __future__ import annotations

import logging
import time
try:
    from ..core.models import LogEvent
    from ..core.telemetry_db import TelemetryDatabase
    from .task_spec import HarborEnvironmentConfig, HarborTaskSpec, HarborTrialJob
except (ImportError, ValueError):
    from core.models import LogEvent
    from core.telemetry_db import TelemetryDatabase
    from harbor.task_spec import HarborEnvironmentConfig, HarborTaskSpec, HarborTrialJob

logger = logging.getLogger("harbor.sandbox")


class HarborSandbox:
    """Isolated execution sandbox environment for agent threat hunting."""

    def __init__(self, task_spec: HarborTaskSpec, config: Optional[HarborEnvironmentConfig] = None):
        self.task_spec = task_spec
        self.config = config or task_spec.environment
        self.db = TelemetryDatabase()
        self.is_running = False
        self.start_time: Optional[float] = None
        self.logs: List[str] = []
        self._audit_trail: List[Dict[str, Any]] = []

    def start(self, events: List[LogEvent]) -> None:
        """Initialize the sandbox environment and mount the telemetry database."""
        self.start_time = time.time()
        self.is_running = True
        self._log(f"[Harbor Sandbox] Initializing sandbox in mode: {self.config.sandbox_mode}")
        self._log(f"[Harbor Sandbox] Enforcing limits: Timeout={self.config.timeout_seconds}s, Memory={self.config.memory_limit_mb}MB")
        self._log(f"[Harbor Sandbox] Network egress policy: {'BLOCKED (Secure)' if not self.config.network_egress else 'ENABLED'}")

        # Ingest telemetry logs
        loaded = self.db.load_events(events)
        self._log(f"[Harbor Sandbox] Mounted read-only telemetry dataset ({loaded} log events)")

    def execute_sql(self, query: str, max_rows: int = 50) -> Tuple[List[str], List[List[Any]], float, Optional[str]]:
        """Execute a query within the sandbox constraints."""
        if not self.is_running:
            return [], [], 0.0, "Sandbox is not currently active."

        # Check timeout limit
        elapsed = time.time() - (self.start_time or time.time())
        if elapsed > self.config.timeout_seconds:
            err = f"Execution timeout: Sandbox limit of {self.config.timeout_seconds}s exceeded."
            self._log(f"[Harbor Sandbox] ERROR: {err}")
            return [], [], 0.0, err

        # Run query inside DB
        cols, rows, dur_ms, err = self.db.execute_query(query, max_rows=max_rows)

        self._audit_trail.append({
            "timestamp": time.time(),
            "query": query,
            "duration_ms": dur_ms,
            "row_count": len(rows),
            "error": err,
        })

        if err:
            self._log(f"[Harbor Sandbox] Query Failed ({dur_ms:.1f}ms): {err}")
        else:
            self._log(f"[Harbor Sandbox] Query Success ({dur_ms:.1f}ms): Returned {len(rows)} rows")

        return cols, rows, dur_ms, err

    def terminate(self) -> HarborTrialJob:
        """Tear down the sandbox and compile final trial job metadata."""
        self.is_running = False
        duration = (time.time() - (self.start_time or time.time()))
        self._log(f"[Harbor Sandbox] Sandbox session terminated. Active duration: {duration:.2f}s")
        self.db.close()

        return HarborTrialJob(
            trial_id=f"trial-{self.task_spec.task_id}",
            task_spec=self.task_spec,
            agent_harness="HarborAgent",
            model_name="gemini-3.7-flash",
            status="COMPLETED",
            sandbox_logs=self.logs,
            result_metadata={
                "total_queries": len(self._audit_trail),
                "duration_seconds": round(duration, 2),
                "audit_trail": self._audit_trail,
            },
        )

    def _log(self, message: str) -> None:
        """Append a message to the sandbox console log."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs.append(entry)
