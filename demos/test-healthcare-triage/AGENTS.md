# Test Healthcare Triage Assistant - AGENTS.md Harness

## 🎯 System Goal & Operational Boundaries
This repository contains the production agent for **Test Healthcare Triage Assistant** using **ADK 2.0 + FastAPI + Vertex AI**.
Operating under **AGENTIC_ENGINEERING** SDLC standards.

---

## 📐 Technology Stack & Conventions
- **Framework**: Google ADK 2.0 / `google-genai` SDK
- **Backend Service**: FastAPI decoupled microservice
- **Frontend Presentation**: Modern Glassmorphism UI
- **Required Pinned Dependencies**:
  - `pyopenssl==24.3.0`
  - `cryptography==44.0.3`

---

## 🛡️ Guardrails & Constraints
1. **Entrypoint Export**: ADK root agent variable MUST be named `root_agent` or `app` in `app/agent.py`.
2. **Environment Variable Naming**: Use `GCP_PROJECT` instead of reserved `GOOGLE_CLOUD_PROJECT`.
3. **Payload Limit**: Keep staging payload (`app/`) under **8MB** payload size for Vertex AI Reasoning Engine.
4. **Dual-Mode Fallback**: Provide offline simulation responses in `app/simulation.py` when GCP credentials are not active.
5. **Quality Gates**: PR merge requires passing `pytest tests/` and passing trajectory evaluation score >= 0.85.
