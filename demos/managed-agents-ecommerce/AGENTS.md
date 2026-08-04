# Managed Agents API - Unified Commerce Agent - AGENTS.md Harness

## 🎯 System Goal & Operational Boundaries
This repository contains the enterprise-grade production agent for **Managed Agents API - Unified Commerce Agent**, deployed on **Vertex AI Managed Agents API / Agent Engine** and integrated with a **Glassmorphism Control Room Web UI**.
Operating under **PRODUCTION** SDLC harness standards.

---

## 📐 Technology Stack & Conventions
- **Framework**: Managed Agents API (`aiplatform.googleapis.com/v1beta1`) & `google-genai` SDK
- **Deployment Target**: Vertex AI Managed Agents API & Gemini Enterprise
- **Backend Service**: FastAPI decoupled microservice (`app.py`)
- **Frontend Presentation**: Modern Glassmorphism Control Room UI (`static/index.html`, `static/main.js`, `static/style.css`)
- **Skills Directive**: Remote GCS-mounted skill playbook (`unified_commerce_skill.md`)
- **Required Pinned Dependencies**:
  - `fastapi>=0.110.0`
  - `uvicorn>=0.28.0`
  - `pydantic>=2.6.0`
  - `google-genai>=2.0.0`
  - `google-auth>=2.28.0`
  - `httpx>=0.27.0`

---

## 🛡️ Guardrails & Operational Constraints
1. **Agent ID Naming**: Control Plane agent configuration ID MUST be `unified-commerce-agent`.
2. **Environment Variable Security**: Use `GCP_PROJECT` instead of reserved `GOOGLE_CLOUD_PROJECT` inside custom code to prevent Vertex AI deployment rejection.
3. **Payload & Storage**: Mount merchant dataset (`merchant_data/`) and skills (`unified_commerce_skill.md`) cleanly into the remote execution container.
4. **Dual-Mode Serving Fallback**: Provide high-fidelity simulation responses when GCP credentials or Managed Agent control plane endpoints are unreachable during customer demos.
5. **Customer Neutrality**: Keep all merchant datasets, system directives, and UI labels customer-agnostic (OmniCommerce Platform / Unified Commerce Agent).
