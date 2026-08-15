"""FastAPI Web Server for Simbian Cyber Defense Benchmark Operations Dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from benchhub.curator import BenchHubCurator
from core.mitre import get_all_tactics, get_tactic_metadata
from evaluation.evaluator import CyberDefenseEvaluator
from evaluation.report_generator import ReportGenerator

WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


class EvaluateRequest(BaseModel):
    scenario_id: str = "simbian-apt29-01"
    harness_name: str = "antigravity"
    model_name: str = "gemini-3.7-flash"
    thinking_budget: int = 2048
    use_live_llm: bool = False
    harbor_sandbox_mode: str = "local-isolated"
    benchhub_slice: str = "all-tactics"


class CompareRequest(BaseModel):
    scenario_id: str = "simbian-apt29-01"
    model_name: str = "gemini-3.7-flash"
    thinking_budget: int = 2048
    use_live_llm: bool = False


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI web application."""
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
        template_path = TEMPLATES_DIR / "index.html"
        if not template_path.exists():
            raise HTTPException(status_code=404, detail="Dashboard template not found.")
        return template_path.read_text(encoding="utf-8")

    @app.get("/api/scenarios")
    async def get_scenarios():
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
        slices = curator.list_slices()
        return [s.model_dump() for s in slices]

    @app.get("/api/mitre-tactics")
    async def get_tactics():
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
    async def evaluate_scenario(req: EvaluateRequest):
        try:
            summary = evaluator.run_evaluation(
                scenario_id=req.scenario_id,
                harness_name=req.harness_name,
                model_name=req.model_name,
                thinking_budget=req.thinking_budget,
                use_live_llm=req.use_live_llm,
                harbor_sandbox_mode=req.harbor_sandbox_mode,
                benchhub_slice=req.benchhub_slice,
            )
            return summary.model_dump()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/compare")
    async def compare_harnesses(req: CompareRequest):
        try:
            harnesses = ["antigravity", "opencode", "baseline"]
            results = []
            for h in harnesses:
                summary = evaluator.run_evaluation(
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
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/skills")
    async def get_skills():
        from core.skills_loader import SkillsRegistry
        registry = SkillsRegistry()
        return {
            "skills": registry.get_skills_list(),
            "agents_spec": registry.get_agents_spec_markdown(),
        }

    @app.get("/api/history")
    async def get_history():
        history = evaluator.list_history()
        return [h.model_dump() for h in history]

    @app.get("/api/run/{run_id}")
    async def get_run_details(run_id: str):
        run = evaluator.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found.")
        return run.model_dump()

    return app
