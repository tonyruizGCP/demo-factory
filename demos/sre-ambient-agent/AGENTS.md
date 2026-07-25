# SRE Ambient Agent - SDLC Harness & Operational Rules

This repository contains the **Ambient SRE Log Triage & Threat Hunting Agent** built with **Google ADK 2.0 (Agent Development Kit)**, **FastAPI**, **Gemini**, and **MCP (Model Context Protocol)**.

---

## 🎯 System Mission & Scope
Event-driven ambient monitoring agent that listens for Pub/Sub push webhooks and Cloud Logging error alerts. Automatically triages low-severity warnings (`INFO`/`WARNING`) and initiates cognitive BigQuery log investigation for high-severity incidents (`ERROR`/`CRITICAL`).

---

## 📐 Stack & Architecture Standards
- **Framework**: Google ADK 2.0 / `google-genai` SDK
- **Backend Service**: FastAPI Webhook Receiver
- **Data Engine**: BigQuery MCP Server (`@modelcontextprotocol/server-bigquery`) via stdio transport
- **Pinned Dependencies**:
  - `google-genai>=2.0.0`
  - `fastapi>=0.110.0`
  - `pydantic-settings>=2.2.0`
  - `pyopenssl==24.3.0`
  - `cryptography==44.0.3`

---

## 🛡️ Guardrails & Hard Constraints
1. **ADK Root Naming**: Export entrypoint in `app/agent.py` MUST be named `root_agent` or `app`.
2. **Environment Variable Security**: Use `GCP_PROJECT` instead of reserved `GOOGLE_CLOUD_PROJECT`.
3. **Payload Footprint**: Keep `app/` staging directory under **8MB** payload limit for Cloud / Vertex AI Reasoning Engine deployment.
4. **Offline Resilience**: Provide full offline simulation fallbacks in `app/simulation.py` for dry-run testing without GCP credentials.
5. **Quality Gates**: CI/CD requires 100% passing `pytest` suite and Trajectory Score $\ge 0.85$.
