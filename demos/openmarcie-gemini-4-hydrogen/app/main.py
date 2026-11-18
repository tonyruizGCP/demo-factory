"""FastAPI server for the OpenMARCIE Vol10 × Gemini 4 Hydrogen Demo."""

import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agent import run_multimodal_analysis
from app.config import CLIP_PATH, FORCE_SIMULATION, GCP_LOCATION, GCP_PROJECT, KEYFRAMES, MODEL_ID, STATIC_DIR

web_app = FastAPI(title="OpenMARCIE Vol10 × Gemini 4 Hydrogen Demo")
web_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class AnalyzeRequest(BaseModel):
    mode: str = "temporal_actions"
    prompt: str = ""
    thinking_level: str = "MEDIUM"


@web_app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@web_app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": MODEL_ID,
        "project": GCP_PROJECT,
        "location": GCP_LOCATION,
        "simulation_forced": FORCE_SIMULATION,
        "clip_ready": CLIP_PATH.exists(),
    }


@web_app.get("/api/media")
def media() -> dict:
    return {
        "video_url": "/static/media/vol10_window_90s_cropped.mp4",
        "keyframes": [
            {"label": label, "url": f"/static/media/{path.name}"}
            for label, path in KEYFRAMES
        ],
    }


@web_app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    return run_multimodal_analysis(
        mode=req.mode,
        custom_prompt=req.prompt,
        thinking_level=req.thinking_level,
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("app.main:web_app", host="0.0.0.0", port=port, reload=False)
