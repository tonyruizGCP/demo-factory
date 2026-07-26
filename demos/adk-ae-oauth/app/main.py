import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional

from app.agent import root_agent
from app.simulation import get_simulated_drive_response

app = FastAPI(
    title="ADK Agent Engine + OAuth - Google Drive Reader",
    description="Enterprise-grade Google Drive Reader agent with 3-stage OAuth credential negotiation."
)

class QueryRequest(BaseModel):
    query: str
    file_id: Optional[str] = None
    force_simulation: Optional[bool] = True

@app.post("/api/query")
async def handle_query(req: QueryRequest):
    # Extract file_id if present in query string or explicitly provided
    file_id = req.file_id
    if not file_id:
        match = re.search(r'([a-zA-Z0-9_-]{25,})', req.query)
        if match:
            file_id = match.group(1)
        else:
            file_id = "1AbCdEfGhIjKlMnOpQrStUvWxYz_12345"

    return get_simulated_drive_response(req.query, file_id)

@app.get("/api/auth/status")
async def auth_status():
    return {
        "status": "configured",
        "oauth_scopes": ["https://www.googleapis.com/auth/drive.readonly"],
        "token_cache_key": os.environ.get("AUTH_ID", "google-drive-auth"),
        "stage_resolution": [
            "Stage 1: tool_context.state['temp:google-drive-auth'] (Gemini Enterprise Injected Token)",
            "Stage 2: tool_context.get_auth_response() (ADK Web UI Flow)",
            "Stage 3: tool_context.request_credential() (User Consent Redirect)"
        ]
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
