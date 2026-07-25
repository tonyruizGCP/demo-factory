# Demo Factory - SDLC Harness & Agent Guidelines

This repository implements the **Demo Factory**, an AI-powered agentic generation engine and Software Development Life Cycle (SDLC) harness built according to the principles of **Agentic Engineering** (Osmani et al., 2026).

---

## 🏛️ Project & Architecture Overview

The Demo Factory takes a **Customer Use Case** and a **Technological Approach** and generates a production-ready demo repository equipped with a complete SDLC harness:
1. **Context Engineering**: Static (`AGENTS.md`) and dynamic context (Agent Skills).
2. **Decoupled Architecture**: Staging backend (`< 8MB` payload limit for Cloud deployment) separated from presentation UI.
3. **Quality Gates & Continuous Evals**: Automated unit tests, trajectory verification, and LM judge rubrics.
4. **Guardrails & Lifecycle Hooks**: GitHub Actions CI/CD workflows, dependency security checks, and secret scanners.
5. **Dual-Mode Serving**: Live Google Cloud / Vertex AI execution with high-fidelity offline simulation fallbacks.

---

## 📐 Stack & Conventions

- **Language & Runtime**: Python 3.11+, FastAPI, Uvicorn, Google ADK 2.0 / `google-genai` SDK.
- **Frontend Presentation**: Modern Glassmorphism Vanilla Web (HTML5, CSS3, ES6 JavaScript) with dynamic streaming and markdown rendering.
- **Testing & Evals**: Pytest, Asyncio test runner, JSON Trajectory Rubrics.
- **Security & Dependencies**:
  - `pyopenssl==24.3.0`
  - `cryptography==44.0.3`
  - Strict no-outbound sandbox egress rules (OpenAPI toolsets for external APIs).
  - Unreserved env var mapping: `GCP_PROJECT` instead of `GOOGLE_CLOUD_PROJECT`.

---

## 🚫 Hard Constraints & Guardrails

1. **ADK Entrypoint Naming**: Root agent instance variable in `app/agent.py` MUST be named `app` or `root_agent`.
2. **Port Binding**: NEVER hardcode `PORT=8080` in `.env` files for cloud staging. Let runtimes bind dynamically.
3. **Payload Isolation**: Keep static web assets and heavy datasets out of staging directories meant for cloud deployment.
4. **Offline Resilience**: All API endpoints MUST provide high-fidelity simulated responses when GCP credentials are not present.

---

## 🔄 SDLC Workflow Loop

```
[Define Specs] -> [Harness Generation] -> [Agent Code & Tools] -> [Automated Evals & Tests] -> [CI/CD Quality Gate] -> [Live/Simulated Demo]
```
