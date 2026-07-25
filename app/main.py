import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.models import (
    GenerateDemoRequest, GeneratedHarnessResponse,
    EvalRunRequest, EvalRunResult,
    RunSimulationRequest, RunSimulationResponse,
    TCOCalculationRequest, TCOCalculationResponse
)
from app.generator import DemoGeneratorEngine
from app.simulation import simulate_agent_run, calculate_tco, PRESET_USE_CASES
from app.eval_runner import execute_eval_suite

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(APP_DIR, "static")

app = FastAPI(
    title="Demo Factory - Agentic Engineering & SDLC Generator",
    description="Generates production-ready demo projects following GitHub SDLC best practices and harness engineering.",
    version="0.1.0"
)

generator_engine = DemoGeneratorEngine()

@app.post("/api/generate", response_model=GeneratedHarnessResponse)
async def generate_demo_project(req: GenerateDemoRequest):
    try:
        res = generator_engine.generate_project(req)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/eval", response_model=EvalRunResult)
async def run_evaluation(req: EvalRunRequest):
    try:
        res = execute_eval_suite(req.project_slug)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate-run", response_model=RunSimulationResponse)
async def run_simulation(req: RunSimulationRequest):
    try:
        res = simulate_agent_run(req.use_case, req.user_input)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tco-calc", response_model=TCOCalculationResponse)
async def compute_tco(req: TCOCalculationRequest):
    try:
        res = calculate_tco(req)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/presets")
async def list_presets():
    return [
        {
            "key": k,
            "title": v["title"],
            "tech": v["tech"],
            "description": v["response"]
        } for k, v in PRESET_USE_CASES.items()
    ]

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
