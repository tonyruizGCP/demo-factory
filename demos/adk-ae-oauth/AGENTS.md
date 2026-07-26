# ADK Agent Engine + OAuth - Google Drive Reader - AGENTS.md Harness

## 🎯 System Goal & Operational Boundaries
This repository contains the enterprise-grade production agent for **Google Drive File Reading via OAuth 2.0**, deployed on **Vertex AI Agent Engine** and integrated with **Gemini Enterprise** and **ADK Web UI**.
Operating under **PRODUCTION** SDLC harness standards.

---

## 📐 Technology Stack & Conventions
- **Framework**: Google ADK 2.0 (`google-adk`) & `google-genai` SDK
- **Deployment Target**: Vertex AI Agent Engine & Gemini Enterprise
- **Authentication**: OAuth 2.0 Three-Stage Credential Resolution (`negotiate_creds`)
- **Backend Service**: FastAPI decoupled microservice
- **Frontend Presentation**: Modern Glassmorphism Presentation UI
- **Required Pinned Dependencies**:
  - `pyopenssl==24.3.0`
  - `cryptography==44.0.3`
  - `google-adk>=0.1.0`
  - `google-api-python-client>=2.100.0`
  - `google-auth-httplib2>=0.2.0`
  - `google-auth-oauthlib>=1.2.0`

---

## 🛡️ Guardrails & Operational Constraints
1. **ADK Root Naming**: Export entrypoint in `app/agent.py` MUST be named `root_agent` or `app`.
2. **Environment Variable Security**: Use `GCP_PROJECT` instead of reserved `GOOGLE_CLOUD_PROJECT` inside custom code to prevent Vertex AI deployment rejection.
3. **Payload Limit**: Keep staging payload (`app/`) under **8MB** size for Vertex AI Agent Engine deployment.
4. **Three-Stage OAuth Negotiation**:
   - Stage 1: Check `tool_context.state` for cached or injected tokens (`temp:<AUTH_ID>`).
   - Stage 2: Check `tool_context.get_auth_response()` for completed ADK OAuth exchange.
   - Stage 3: Call `tool_context.request_credential()` to initiate consent flow.
5. **Dual-Mode Serving Fallback**: Provide offline simulation responses in `app/simulation.py` when GCP credentials or OAuth user consent are not active during customer demos.
6. **Quality Gates**: PR merge requires passing 100% of deterministic `pytest` unit tests and achieving a Trajectory Quality Score $\ge 0.85$.
