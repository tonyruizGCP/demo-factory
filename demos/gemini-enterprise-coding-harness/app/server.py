"""FastAPI Backend Server with SSE Streaming for Gemini Enterprise Coding Harness.

Exposes:
- `POST /api/chat/stream`: Server-Sent Events (SSE) stream for agent execution
- `GET /api/session/{id}`: Session state, turn history, and rewind
- `POST /api/session/{id}/rewind`: Replay / rewind to a specific turn
- `GET /api/memory`: Memory Bank records
- `POST /api/memory`: Add new memory guideline
- Mounts `/` to static web visualizer
"""

import asyncio
import json
import logging
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from pydantic import BaseModel

from app.agent import CodingHarnessOrchestrator
from app.config import get_config

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gemini Enterprise Coding Harness",
    description="Enterprise-grade AI agent harness demo matching the Stencil Harness Playbook",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
orchestrator = CodingHarnessOrchestrator(workspace_root=".")


class ChatRequest(BaseModel):
    session_id: str = "default-demo-session"
    prompt: str


class RewindRequest(BaseModel):
    turn_id: str


class BranchRequest(BaseModel):
    branch_name: str
    from_turn_id: Optional[str] = None


class MemoryCreateRequest(BaseModel):
    category: Optional[str] = "guideline"
    content: str


@app.get("/api/status")
def get_status():
    """Returns harness health, active backend modes, and environment configuration."""
    return {
        "status": "HEALTHY",
        "mode": (
            "managed"
            if (
                orchestrator.session_manager.is_managed
                or orchestrator.memory_bank.is_managed
            )
            else "local"
        ),
        "services": {
            "sessions": {
                "mode": orchestrator.session_manager.mode,
                "backend": (
                    "VertexAiSessionService"
                    if orchestrator.session_manager.is_managed
                    else "InMemorySessionService"
                ),
            },
            "memory_bank": {
                "mode": orchestrator.memory_bank.mode,
                "backend": (
                    "MemoryBankServiceClient"
                    if orchestrator.memory_bank.is_managed
                    else "InMemoryMemoryBank"
                ),
            },
        },
        "project_id": orchestrator.project_id,
        "location": orchestrator.location,
        "agent_engine_id": orchestrator.agent_engine_id,
    }


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    """Streams intermediate agent thoughts, tool calls, and final output using SSE."""
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    session_id = req.session_id.strip() if req.session_id and req.session_id.strip() else "default-demo-session"

    async def event_generator():
        try:
            async for item in orchestrator.execute_task_stream(session_id, req.prompt.strip()):
                if await request.is_disconnected():
                    logger.info("Client disconnected from SSE stream (session_id=%s)", session_id)
                    break
                yield f"data: {json.dumps(item, default=str)}\n\n"
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            logger.info("SSE stream task cancelled for session=%s", session_id)
            raise
        except Exception as e:
            logger.error("SSE stream error for session=%s: %s", session_id, e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, default=str)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/session/{session_id}")
def get_session(session_id: str):
    sid = session_id.strip() if session_id and session_id.strip() else "default-demo-session"
    sess = orchestrator.session_manager.get_or_create(sid)
    return {
        "session_id": sess.session_id,
        "mode": orchestrator.session_manager.mode,
        "branch": sess.branch_name,
        "parent_session_id": sess.parent_session_id,
        "turns": [
            {
                "turn_id": t.turn_id,
                "role": t.role,
                "content": t.content,
                "timestamp": t.timestamp,
                "tool_calls": t.tool_calls,
                "tool_outputs": t.tool_outputs,
            }
            for t in sess.turns
        ],
        "state": sess.state,
    }


@app.post("/api/session/{session_id}/rewind")
def rewind_session(session_id: str, req: RewindRequest):
    if not session_id or not session_id.strip():
        raise HTTPException(status_code=400, detail="session_id cannot be empty")
    if not req.turn_id or not req.turn_id.strip():
        raise HTTPException(status_code=400, detail="turn_id cannot be empty")
    sess = orchestrator.session_manager.get_or_create(session_id.strip())
    success = sess.rewind_to_turn(req.turn_id.strip())
    if not success:
        raise HTTPException(status_code=404, detail="Turn ID not found")
    return {
        "status": "REWOUND",
        "mode": orchestrator.session_manager.mode,
        "remaining_turns": len(sess.turns),
    }


@app.post("/api/session/{session_id}/branch")
def branch_session(session_id: str, req: BranchRequest):
    if not session_id or not session_id.strip():
        raise HTTPException(status_code=400, detail="session_id cannot be empty")
    if not req.branch_name or not req.branch_name.strip():
        raise HTTPException(status_code=400, detail="branch_name cannot be empty")

    sid = session_id.strip()
    with orchestrator.session_manager._lock:
        if sid not in orchestrator.session_manager._sessions:
            raise HTTPException(status_code=404, detail=f"Session '{sid}' not found")

    try:
        child = orchestrator.session_manager.branch_session(
            session_id=sid,
            new_branch_name=req.branch_name.strip(),
            from_turn_id=req.from_turn_id.strip() if req.from_turn_id else None,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        msg = str(e)
        status_code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=status_code, detail=msg)

    return {
        "status": "BRANCHED",
        "session_id": child.session_id,
        "parent_session_id": sid,
        "branch": child.branch_name,
        "turn_count": len(child.turns),
        "mode": orchestrator.session_manager.mode,
    }


@app.get("/api/memory")
def get_memories(
    query: Optional[str] = None,
    category: Optional[str] = None,
    top_k: int = 5,
):
    if query and query.strip():
        cleaned_top_k = max(1, min(top_k, 50))
        cat = category.strip() if category and category.strip() else None
        records = orchestrator.memory_bank.query_memories(
            query=query.strip(), category=cat, top_k=cleaned_top_k
        )
        memories = [
            {
                "id": m.memory_id,
                "category": m.category,
                "content": m.content,
                "metadata": m.metadata,
                "timestamp": m.timestamp,
            }
            for m in records
        ]
    else:
        memories = orchestrator.memory_bank.list_all()

    return {
        "mode": orchestrator.memory_bank.mode,
        "memories": memories,
    }


@app.post("/api/memory")
def add_memory(req: MemoryCreateRequest):
    if not req.content or not req.content.strip():
        raise HTTPException(status_code=400, detail="Memory content cannot be empty")
    cat = req.category.strip() if req.category and req.category.strip() else "guideline"
    rec = orchestrator.memory_bank.record_memory(
        category=cat,
        content=req.content.strip(),
        metadata={"source": "Manual User Ingestion"},
    )
    return {
        "status": "RECORDED",
        "mode": orchestrator.memory_bank.mode,
        "memory_id": rec.memory_id,
    }


# Mount static assets
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def get_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Gemini Enterprise Coding Harness API</h1><p>Static UI loading...</p>")


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Gemini Enterprise Coding Harness Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")), help="Server port")
    parser.add_argument("--use-managed-services", action="store_true", default=None, help="Enable Vertex AI managed backends")
    parser.add_argument("--no-managed-services", dest="use_managed_services", action="store_false", help="Disable Vertex AI managed backends")
    parser.add_argument("--use-managed-sessions", action="store_true", default=None, help="Enable managed sessions backend")
    parser.add_argument("--no-managed-sessions", dest="use_managed_sessions", action="store_false", help="Disable managed sessions backend")
    parser.add_argument("--use-managed-memory-bank", action="store_true", default=None, help="Enable managed memory bank backend")
    parser.add_argument("--no-managed-memory-bank", dest="use_managed_memory_bank", action="store_false", help="Disable managed memory bank backend")
    parser.add_argument("--project-id", default=None, help="Google Cloud project ID")
    parser.add_argument("--location", default=None, help="Google Cloud location")
    parser.add_argument("--agent-engine-id", default=None, help="Agent engine resource ID")
    args, _ = parser.parse_known_args()

    if args.use_managed_services is not None:
        os.environ["USE_MANAGED_SERVICES"] = "true" if args.use_managed_services else "false"
    if args.use_managed_sessions is not None:
        os.environ["USE_MANAGED_SESSIONS"] = "true" if args.use_managed_sessions else "false"
    if args.use_managed_memory_bank is not None:
        os.environ["USE_MANAGED_MEMORY_BANK"] = "true" if args.use_managed_memory_bank else "false"
    if args.project_id:
        os.environ["GCP_PROJECT"] = args.project_id
    if args.location:
        os.environ["GOOGLE_CLOUD_LOCATION"] = args.location
    if args.agent_engine_id:
        os.environ["GOOGLE_CLOUD_AGENT_ENGINE_ID"] = args.agent_engine_id

    # Re-initialize orchestrator with reloaded config
    fresh_config = get_config(reload=True)
    orchestrator = CodingHarnessOrchestrator(workspace_root=".", config=fresh_config)

    uvicorn.run(app, host=args.host, port=args.port)
