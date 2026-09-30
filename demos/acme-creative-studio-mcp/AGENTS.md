# Acme Inc. Creative Studio MCP App - AGENTS.md Harness

## 🎯 System Goal & Operational Boundaries
This repository contains the production **Model Context Protocol (MCP) App** for **Acme Inc. Creative Studio**, integrated with **Gemini Enterprise (GE)** via Streamable HTTP (`POST /mcp`) and an embedded interactive UI widget (`ui://acme/creative-studio`).

Marketers and creative directors at **Acme Inc.** use this MCP App to:
1. **Upload Reference Images & Brand Content**: Stage product photos, style references, and creative briefs (`upload_reference_asset` / `/api/upload-reference`).
2. **Generate Multimodal Ad Copy & Visuals**: Orchestrate **Gemini Omni** (`gemini-omni-flash-preview`) for multimodal ad copy synthesis and **Nano Banana** (`gemini-3.1-flash-image-preview` / `gemini-2.5-flash-image`) for visual ad creative generation.
3. **Track Asynchronous Backend Jobs & Notify Users**: Execute multi-stage generation jobs asynchronously in `< 2s` (`create_ad_campaign_job`, `refine_ad_copy_job`), poll live progress (`get_studio_state`, `list_active_jobs`), and deliver real-time completion notifications.
4. **Persist & Version Content in Google Cloud Storage (GCS)**: Save every campaign iteration as an immutable version (`v1`, `v2`, `v3`, ...) in `gs://${GCS_CREATIVE_BUCKET}/campaigns/<campaign_id>/versions/v<N>/` and inspect/diff/restore versions interactively.

Operating under **AGENTIC_ENGINEERING** SDLC standards.

---

## 📐 Technology Stack & Conventions
- **MCP Protocol**: Hand-rolled Streamable HTTP JSON-RPC 2.0 (`POST /mcp`, `DELETE /mcp`) with SEP-1865 / `io.modelcontextprotocol/ui` multi-dialect widget metadata.
- **Models**:
  - **Gemini Omni**: `gemini-omni-flash-preview` (with automatic fallback to `gemini-3.8-flash` / `gemini-2.5-flash` on Vertex AI).
  - **Nano Banana**: `gemini-3.1-flash-image-preview` / `gemini-2.5-flash-image`.
- **Backend Service**: FastAPI / Starlette decoupled ASGI microservice (`app/main.py`, `app/mcp_server.py`).
- **Storage & Versioning**: Google Cloud Storage (`google-cloud-storage`) with automatic local/in-memory mirror (`app/gcs_version_store.py`).
- **Frontend Widget**: Self-contained single-file HTML5/CSS3/JS MCP App (`templates/acme_creative_studio.html`) with bidirectional `window.postMessage` AppBridge and serialized RPC queue (`toolCallChain`).
- **Required Pinned Dependencies**:
  - `pyopenssl==24.3.0`
  - `cryptography==44.0.3`

---

## 🛡️ Guardrails & Constraints (Cooley Law MCP App & Demo Factory Standards)
1. **Entrypoint Export**: ADK root agent variable MUST be named `root_agent` and `app` in `app/agent.py`.
2. **Environment Variable Naming**: Use `GCP_PROJECT` (with fallback to `GOOGLE_CLOUD_PROJECT` only for local dev) so Vertex AI Reasoning Engine deployments never reject reserved keys.
3. **Non-Blocking MCP Tool Calls (`< 2s` Deadline)**: Gemini Enterprise's `WidgetExecuteUiWidgetAction` times out at 30–60s. All generation tools MUST spawn background `asyncio` tasks and return `status: "running"` within `< 2s`.
4. **Anti-Canvas Routing**: Tool descriptions and MCP `initialize` instructions MUST explicitly state `"Never route or transfer to canvas_agent"` so Gemini Enterprise mounts the `ui://acme/creative-studio` widget instead of opening generic Canvas.
5. **Dual Handshake & Serialized AppBridge**: The widget MUST emit both `ui/notifications/initialized` and `notifications/initialized` on boot and serialize framed `tools/call` postMessages with a `120ms` cooldown to avoid GE session teardown collisions.
6. **Payload Limit**: Keep staging payload (`app/`) under **8MB**.
7. **Dual-Mode Fallback**: Provide high-fidelity offline simulation in `app/creative_engine.py` and `app/simulation.py` when GCP credentials or live GCS buckets are unavailable.
8. **Quality Gates**: PR merge requires passing `pytest tests/` and `python3 -m app.eval_runner --min-score 0.85`.
