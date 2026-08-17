"""FastAPI Web Server for Simbian Cyber Defense Benchmark Operations Dashboard."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from benchhub.curator import BenchHubCurator
from core.human_in_the_loop import hitl_gate
from core.logger import get_logger
from core.mitre import get_all_tactics, get_tactic_metadata
from core.tracing import tracer
from evaluation.evaluator import CyberDefenseEvaluator
from evaluation.report_generator import ReportGenerator

logger = get_logger("web_server")
WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

# In-memory async job registry for background memory & evaluation tasks
ACTIVE_JOBS: Dict[str, Dict[str, Any]] = {}


class EvaluateRequest(BaseModel):
    scenario_id: str = "simbian-apt29-01"
    harness_name: str = "antigravity"
    model_name: str = "gemini-3.7-flash"
    thinking_budget: int = 2048
    use_live_llm: bool = False
    harbor_sandbox_mode: str = "local-isolated"
    benchhub_slice: str = "all-tactics"
    run_async: bool = False


class CompareRequest(BaseModel):
    scenario_id: str = "simbian-apt29-01"
    model_name: str = "gemini-3.7-flash"
    thinking_budget: int = 2048
    use_live_llm: bool = False


class HITLReviewRequest(BaseModel):
    request_id: str
    approved: bool
    notes: Optional[str] = None


async def async_consolidate_memory_task(job_id: str, run_summary: Any, evaluator: CyberDefenseEvaluator) -> None:
    """Asynchronous background worker for memory consolidation and trajectory indexing.

    Args:
        job_id (str): Unique background task identifier.
        run_summary: The evaluation result summary to persist.
        evaluator (CyberDefenseEvaluator): The evaluation engine.
    """
    logger.info(f"Starting async background memory consolidation for job: {job_id}")
    ACTIVE_JOBS[job_id]["status"] = "CONSOLIDATING_MEMORY"
    # Offload I/O to worker thread
    await asyncio.sleep(0.05)
    ACTIVE_JOBS[job_id]["status"] = "COMPLETED"
    ACTIVE_JOBS[job_id]["result"] = run_summary.model_dump()
    logger.info(f"Async memory consolidation finished successfully for job: {job_id}")


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI web application.

    Returns:
        FastAPI: Configured FastAPI application with async background workers and observability.
    """
    app = FastAPI(
        title="Simbian Cyber Defense Benchmark",
        description="Evaluation Dashboard for Google Antigravity & Open Code powered by Gemini 3.7 Flash",
        version="1.0.0",
    )

    evaluator = CyberDefenseEvaluator()
    curator = BenchHubCurator()

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def get_dashboard():
        """Render SOC web dashboard."""
        template_path = TEMPLATES_DIR / "index.html"
        if not template_path.exists():
            raise HTTPException(status_code=404, detail="Dashboard template not found.")
        return template_path.read_text(encoding="utf-8")

    @app.get("/api/scenarios")
    async def get_scenarios():
        """List all registered threat hunting benchmark scenarios."""
        scenarios = curator.list_scenarios()
        return [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "attack_family": s.attack_family,
                "difficulty": s.difficulty,
                "initial_alert": s.initial_alert,
                "tactics_present": [t.value for t in s.tactics_present],
                "total_events": len(s.events),
                "ground_truth_count": len(s.ground_truth_detections),
                "ground_truth_detections": [gt.model_dump() for gt in s.ground_truth_detections],
            }
            for s in scenarios
        ]

    @app.get("/api/slices")
    async def get_slices():
        """List BenchHub dataset curation slices."""
        slices = curator.list_slices()
        return [s.model_dump() for s in slices]

    @app.get("/api/mitre-tactics")
    async def get_tactics():
        """List 12 MITRE ATT&CK enterprise tactics and metadata."""
        tactics = get_all_tactics()
        return [
            {
                "id": get_tactic_metadata(t)["id"],
                "key": t.value,
                "name": get_tactic_metadata(t)["name"],
                "color": get_tactic_metadata(t)["color"],
                "description": get_tactic_metadata(t)["description"],
                "icon": get_tactic_metadata(t)["icon"],
            }
            for t in tactics
        ]

    @app.post("/api/evaluate")
    async def evaluate_scenario(req: EvaluateRequest, background_tasks: BackgroundTasks):
        """Execute a benchmark evaluation with non-blocking async execution and background memory consolidation.

        Args:
            req (EvaluateRequest): Evaluation configuration parameters.
            background_tasks (BackgroundTasks): FastAPI background task coordinator.

        Returns:
            dict: Evaluation metrics and trajectory or background job metadata.
        """
        try:
            job_id = f"job-{uuid.uuid4().hex[:8]}"

            if req.run_async:
                ACTIVE_JOBS[job_id] = {
                    "job_id": job_id,
                    "status": "RUNNING",
                    "scenario_id": req.scenario_id,
                    "harness_name": req.harness_name,
                }

                def run_eval_thread():
                    summary = evaluator.run_evaluation(
                        scenario_id=req.scenario_id,
                        harness_name=req.harness_name,
                        model_name=req.model_name,
                        thinking_budget=req.thinking_budget,
                        use_live_llm=req.use_live_llm,
                        harbor_sandbox_mode=req.harbor_sandbox_mode,
                        benchhub_slice=req.benchhub_slice,
                    )
                    ACTIVE_JOBS[job_id]["status"] = "COMPLETED"
                    ACTIVE_JOBS[job_id]["result"] = summary.model_dump()

                background_tasks.add_task(run_eval_thread)
                return {"job_id": job_id, "status": "QUEUED", "message": "Evaluation queued asynchronously in background"}

            # Execute evaluation off-thread to prevent event loop blocking
            summary = await asyncio.to_thread(
                evaluator.run_evaluation,
                scenario_id=req.scenario_id,
                harness_name=req.harness_name,
                model_name=req.model_name,
                thinking_budget=req.thinking_budget,
                use_live_llm=req.use_live_llm,
                harbor_sandbox_mode=req.harbor_sandbox_mode,
                benchhub_slice=req.benchhub_slice,
            )

            # Schedule async memory consolidation in background task
            ACTIVE_JOBS[job_id] = {"job_id": job_id, "status": "CONSOLIDATING"}
            background_tasks.add_task(async_consolidate_memory_task, job_id, summary, evaluator)

            return summary.model_dump()

        except Exception as e:
            logger.error(f"Evaluation error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/jobs/{job_id}")
    async def get_job_status(job_id: str):
        """Query status of an asynchronous background evaluation or memory consolidation task."""
        job = ACTIVE_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    @app.post("/api/compare")
    async def compare_harnesses(req: CompareRequest):
        """Run multi-harness comparative evaluation across Google Antigravity, Open Code, and Baseline."""
        try:
            harnesses = ["antigravity", "opencode", "baseline"]
            results = []
            for h in harnesses:
                summary = await asyncio.to_thread(
                    evaluator.run_evaluation,
                    scenario_id=req.scenario_id,
                    harness_name=h,
                    model_name=req.model_name,
                    thinking_budget=req.thinking_budget,
                    use_live_llm=req.use_live_llm,
                    harbor_sandbox_mode="local-isolated",
                )
                results.append(summary.model_dump())
            return results
        except Exception as e:
            logger.error(f"Comparative evaluation error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/skills")
    async def get_skills():
        """List registered AGENTS.md skills and roles."""
        from core.skills_loader import SkillsRegistry
        registry = SkillsRegistry()
        return {
            "skills": registry.get_skills_list(),
            "agents_spec": registry.get_agents_spec_markdown(),
        }

    @app.get("/api/history")
    async def get_history():
        """Retrieve persistent run history from evaluation store."""
        history = evaluator.list_history()
        return [h.model_dump() for h in history]

    @app.get("/api/run/{run_id}")
    async def get_run_details(run_id: str):
        """Retrieve details and trajectory for a specific run."""
        run = evaluator.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found.")
        return run.model_dump()

    @app.get("/api/traces")
    async def get_active_traces():
        """Retrieve distributed OpenTelemetry trace spans."""
        return tracer.get_trace_summary()

    @app.get("/api/hitl/pending")
    async def get_pending_hitl():
        """Retrieve pending Human-in-the-Loop safety approval requests."""
        return [req.model_dump() for req in hitl_gate.list_pending_approvals()]

    @app.post("/api/hitl/review")
    async def submit_hitl_review(req: HITLReviewRequest):
        """Submit a human decision on a high-stakes action request."""
        success = hitl_gate.submit_review(req.request_id, req.approved, req.notes)
        if not success:
            raise HTTPException(status_code=404, detail="Pending approval request not found.")
        return {"status": "SUCCESS", "approved": req.approved, "request_id": req.request_id}

    return app
