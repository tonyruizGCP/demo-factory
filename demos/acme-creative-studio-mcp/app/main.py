"""FastAPI + MCP Streamable HTTP Server entrypoint for Acme Inc. Creative Studio."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app.agent import GEMINI_OMNI_MODEL, NANO_BANANA_MODEL, root_agent
from app.mcp_server import register_mcp_routes, studio_runtime
from app.simulation import get_simulated_response

load_dotenv()

app = FastAPI(
    title="Acme Inc. Creative Studio — Gemini Enterprise MCP App",
    description=(
        "Interactive Multimodal Ad Copy & Visual Creative Studio powered by "
        "Gemini Omni + Nano Banana, with GCS Content Versioning and Async Job Tracking."
    ),
    version="1.0.0",
)

# Sandboxed gstatic.com iframes send Origin: null when making direct HTTP calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

# Register Streamable HTTP MCP routes (/mcp, /download/{token}, /api/upload-reference)
register_mcp_routes(app, studio_runtime)


class QueryRequest(BaseModel):
    prompt: str = Field(..., description="User prompt or creative brief instruction")
    campaign_id: str = Field(
        default="acme_trailblazer_x1",
        description="Target Acme Inc. campaign identifier",
    )
    simulation_mode: bool = Field(
        default=True,
        description="Run deterministic Demo Factory simulation or invoke MCP studio tools",
    )


@app.get("/health")
@app.get("/healthz")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "acme-creative-studio-mcp",
        "customer": "Acme Inc.",
        "agent_name": root_agent.name,
        "models": {
            "gemini_omni": GEMINI_OMNI_MODEL,
            "nano_banana": NANO_BANANA_MODEL,
        },
        "gcs_bucket": studio_runtime.gcs_store.bucket_name,
        "mcp_endpoint": "/mcp",
        "ui_resource_uri": "ui://acme/creative-studio",
    }


@app.get("/", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
@app.get("/ui", response_class=HTMLResponse)
async def serve_creative_studio_ui(
    campaign_id: str = Query(default="acme_trailblazer_x1"),
) -> HTMLResponse:
    html_content = studio_runtime.render_widget_html(campaign_id=campaign_id)
    return HTMLResponse(content=html_content)


@app.get("/api/studio-state")
async def api_studio_state(
    campaign_id: str = Query(default="acme_trailblazer_x1"),
    version_number: Optional[int] = Query(default=None),
) -> JSONResponse:
    state = studio_runtime.build_studio_state(
        campaign_id=campaign_id, version_number=version_number
    )
    return JSONResponse(state)


@app.get("/api/jobs")
async def api_list_jobs(
    campaign_id: Optional[str] = Query(default=None),
) -> JSONResponse:
    return JSONResponse(
        {
            "jobs": studio_runtime.job_manager.list_jobs(campaign_id=campaign_id),
            "unread_notifications": studio_runtime.job_manager.list_notifications(
                campaign_id=campaign_id, unread_only=True
            ),
        }
    )


@app.get("/api/versions")
async def api_list_versions(
    campaign_id: str = Query(default="acme_trailblazer_x1"),
) -> JSONResponse:
    versions = studio_runtime.gcs_store.list_versions_sync(campaign_id)
    return JSONResponse(
        {
            "campaign_id": campaign_id,
            "gcs_bucket": studio_runtime.gcs_store.bucket_name,
            "versions": versions,
        }
    )


@app.post("/api/query")
async def api_query(req: QueryRequest) -> JSONResponse:
    sim = get_simulated_response(req.prompt)
    state = studio_runtime.build_studio_state(req.campaign_id)
    return JSONResponse(
        {
            "status": "success",
            "customer": "Acme Inc.",
            "agent": root_agent.name,
            "response": sim.get("response") or sim.get("agent_response"),
            "trajectory": sim.get("trajectory") or sim.get("tool_calls"),
            "thought_process": sim.get("thought_process", []),
            "eval_scores": sim.get("eval_scores", {}),
            "studio_state": state,
        }
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
