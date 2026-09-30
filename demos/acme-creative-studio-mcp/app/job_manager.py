"""Asynchronous Backend Job State Machine & User Notification Tracker.

Implements the Cooley Law MCP App non-blocking `< 2s` tool execution pattern:
- Long-running multimodal generation tasks (Gemini Omni copywriting + Nano Banana
  image synthesis + GCS bucket versioning) run on background `asyncio` tasks.
- Every job transitions through explicit stages (`0% -> 100%`) and emits structured
  notifications into a per-session/global notification queue so the Creative Studio
  MCP App widget and Gemini Enterprise assistant can notify the user immediately.
"""

from __future__ import annotations

import asyncio
import copy
import threading
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Callable, Coroutine


def _utc_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


JOB_QUEUED = "queued"
JOB_RUNNING = "running"
JOB_COMPLETED = "completed"
JOB_FAILED = "failed"
JOB_CANCELLED = "cancelled"


class CreativeJobManager:
    """Tracks active/completed background jobs and real-time user notifications."""

    def __init__(self, max_jobs: int = 100, max_notifications: int = 100) -> None:
        self._lock = threading.RLock()
        self._max_jobs = max_jobs
        self._max_notifications = max_notifications
        self._jobs: dict[str, dict[str, Any]] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._notifications: list[dict[str, Any]] = []

    def create_job(
        self,
        campaign_id: str,
        job_type: str,
        title: str,
        prompt_summary: str = "",
        models: list[str] | None = None,
    ) -> dict[str, Any]:
        """Creates a new job record in `queued` state and emits a start notification."""
        job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        now_iso = _utc_iso()
        job_record: dict[str, Any] = {
            "job_id": job_id,
            "campaign_id": campaign_id,
            "job_type": job_type,  # "full_campaign" | "refine_copy" | "visual_remix"
            "title": title,
            "prompt_summary": prompt_summary,
            "models": models or ["gemini-omni-flash-preview", "gemini-3.1-flash-image-preview (Nano Banana)"],
            "status": JOB_QUEUED,
            "progress_pct": 5.0,
            "current_stage": "Queued — initializing Gemini Omni & Nano Banana pipeline…",
            "stages_log": [
                {
                    "timestamp": now_iso,
                    "stage": "Job created and queued on backend worker",
                    "progress_pct": 5.0,
                }
            ],
            "created_at": now_iso,
            "updated_at": now_iso,
            "completed_at": None,
            "elapsed_seconds": 0.0,
            "_start_ts": time.time(),
            "result_version_id": None,
            "result_gcs_uri": None,
            "result_headline": None,
            "error": None,
        }

        with self._lock:
            self._jobs[job_id] = job_record
            while len(self._jobs) > self._max_jobs:
                oldest_key = next(iter(self._jobs))
                self._jobs.pop(oldest_key, None)

            self._push_notification_locked(
                job_id=job_id,
                campaign_id=campaign_id,
                event_type="job_started",
                severity="info",
                title=f"🚀 Job Started: {title}",
                message=f"Backend job {job_id} started ({ ', '.join(job_record['models']) }).",
            )

        return self._public_job(job_record)

    def update_job_progress(
        self,
        job_id: str,
        stage_text: str,
        progress_pct: float,
    ) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job["status"] in (JOB_COMPLETED, JOB_FAILED, JOB_CANCELLED):
                return None
            now_iso = _utc_iso()
            job["status"] = JOB_RUNNING
            job["current_stage"] = stage_text
            job["progress_pct"] = round(min(max(float(progress_pct), 0.0), 99.0), 1)
            job["updated_at"] = now_iso
            job["elapsed_seconds"] = round(time.time() - job["_start_ts"], 2)
            job["stages_log"].append({
                "timestamp": now_iso,
                "stage": stage_text,
                "progress_pct": job["progress_pct"],
            })
            return self._public_job(job)

    def complete_job(
        self,
        job_id: str,
        version_record: dict[str, Any],
        summary_message: str | None = None,
    ) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            now_iso = _utc_iso()
            version_id = version_record.get("version_id", "v1")
            gcs_uri = (version_record.get("gcs") or {}).get("bundle_gcs_uri", "")
            headline = (version_record.get("ad_copy") or {}).get("headline", "")

            job["status"] = JOB_COMPLETED
            job["progress_pct"] = 100.0
            job["current_stage"] = f"✅ Completed — Saved {version_id} to {gcs_uri}"
            job["updated_at"] = now_iso
            job["completed_at"] = now_iso
            job["elapsed_seconds"] = round(time.time() - job["_start_ts"], 2)
            job["result_version_id"] = version_id
            job["result_gcs_uri"] = gcs_uri
            job["result_headline"] = headline
            job["stages_log"].append({
                "timestamp": now_iso,
                "stage": job["current_stage"],
                "progress_pct": 100.0,
            })

            msg = summary_message or (
                f"Version {version_id} ('{headline[:48]}') generated by Gemini Omni + "
                f"Nano Banana and committed to {gcs_uri} in {job['elapsed_seconds']:.1f}s."
            )
            self._push_notification_locked(
                job_id=job_id,
                campaign_id=job["campaign_id"],
                event_type="job_completed",
                severity="success",
                title=f"✨ Creative Ready ({version_id}): {job['title']}",
                message=msg,
                version_id=version_id,
                gcs_uri=gcs_uri,
            )
            return self._public_job(job)

    def fail_job(self, job_id: str, error_message: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            now_iso = _utc_iso()
            job["status"] = JOB_FAILED
            job["error"] = error_message
            job["current_stage"] = f"❌ Failed: {error_message}"
            job["updated_at"] = now_iso
            job["completed_at"] = now_iso
            job["elapsed_seconds"] = round(time.time() - job["_start_ts"], 2)
            job["stages_log"].append({
                "timestamp": now_iso,
                "stage": job["current_stage"],
                "progress_pct": job["progress_pct"],
            })
            self._push_notification_locked(
                job_id=job_id,
                campaign_id=job["campaign_id"],
                event_type="job_failed",
                severity="error",
                title=f"⚠️ Job Failed: {job['title']}",
                message=error_message,
            )
            return self._public_job(job)

    def spawn_background_job(
        self,
        job_id: str,
        coro_factory: Callable[[], Coroutine[Any, Any, None]],
    ) -> asyncio.Task[Any]:
        """Schedules the async job coroutine on the running event loop."""
        loop = asyncio.get_running_loop()
        task = loop.create_task(coro_factory())
        with self._lock:
            self._tasks[job_id] = task

        def _cleanup(done_task: asyncio.Task[Any]) -> None:
            with self._lock:
                self._tasks.pop(job_id, None)
            if not done_task.cancelled() and done_task.exception() is not None:
                exc = done_task.exception()
                self.fail_job(job_id, f"{type(exc).__name__}: {exc}")

        task.add_done_callback(_cleanup)
        return task

    async def wait_for_job(self, job_id: str, timeout: float = 15.0) -> dict[str, Any] | None:
        """Helper for deterministic tests to await a background job completion."""
        task = self._tasks.get(job_id)
        if task is not None:
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if job["status"] in (JOB_QUEUED, JOB_RUNNING):
                job["elapsed_seconds"] = round(time.time() - job["_start_ts"], 2)
            return self._public_job(job)

    def list_jobs(
        self,
        campaign_id: str | None = None,
        only_active: bool = False,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._jobs.values())
            if campaign_id:
                items = [j for j in items if j["campaign_id"] == campaign_id]
            if only_active:
                items = [j for j in items if j["status"] in (JOB_QUEUED, JOB_RUNNING)]
            for j in items:
                if j["status"] in (JOB_QUEUED, JOB_RUNNING):
                    j["elapsed_seconds"] = round(time.time() - j["_start_ts"], 2)
            items.reverse()
            return [self._public_job(j) for j in items[:limit]]

    # ------------------------------------------------------------------
    # Notifications Queue
    # ------------------------------------------------------------------

    def _push_notification_locked(
        self,
        job_id: str,
        campaign_id: str,
        event_type: str,
        severity: str,
        title: str,
        message: str,
        version_id: str | None = None,
        gcs_uri: str | None = None,
    ) -> dict[str, Any]:
        notif = {
            "notification_id": f"ntf_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}",
            "job_id": job_id,
            "campaign_id": campaign_id,
            "event_type": event_type,
            "severity": severity,  # "info" | "success" | "error"
            "title": title,
            "message": message,
            "version_id": version_id,
            "gcs_uri": gcs_uri,
            "created_at": _utc_iso(),
            "acknowledged": False,
        }
        self._notifications.append(notif)
        while len(self._notifications) > self._max_notifications:
            self._notifications.pop(0)
        return notif

    def list_notifications(
        self,
        campaign_id: str | None = None,
        unread_only: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._notifications)
            if campaign_id:
                items = [n for n in items if n["campaign_id"] == campaign_id]
            if unread_only:
                items = [n for n in items if not n["acknowledged"]]
            items.reverse()
            return copy.deepcopy(items[:limit])

    def acknowledge_notifications(
        self,
        notification_ids: list[str] | None = None,
        campaign_id: str | None = None,
        acknowledge_all: bool = False,
    ) -> int:
        count = 0
        id_set = set(notification_ids or [])
        with self._lock:
            for n in self._notifications:
                if n["acknowledged"]:
                    continue
                if acknowledge_all:
                    if not campaign_id or n["campaign_id"] == campaign_id:
                        n["acknowledged"] = True
                        count += 1
                elif n["notification_id"] in id_set:
                    n["acknowledged"] = True
                    count += 1
        return count

    @staticmethod
    def _public_job(job: dict[str, Any]) -> dict[str, Any]:
        return {k: copy.deepcopy(v) for k, v in job.items() if not k.startswith("_")}
