# 🧠 Demo Factory & Agentic Engineering: Learnings & Retrospective

This document captures the architectural challenges, solutions, lessons learned, and best practices derived while building the **Demo Factory** and replicating the **Ambient SRE Triage Agent**.

Derived from:
> **"The New SDLC With Vibe Coding: From ad-hoc prompting to Agentic Engineering"** (Osmani, Saboo, & Kartakis, May 2026)  
> **Second Brain Knowledge Vault** (`knowledge-vault/obsidian-jetski/`)

---

## 🎯 Executive Summary

Moving from casual **Vibe Coding** (ad-hoc natural language prompting without verification) to **Agentic Engineering** (structured context, automated quality gates, and harness engineering) fundamentally shifts the developer's role from writing syntax to designing the system that builds software.

| Dimension | Casual Vibe Coding | Agentic Engineering (Demo Factory Standard) |
| :--- | :--- | :--- |
| **Intent Specification** | Informal prompts | Formal `AGENTS.md` specs, static/dynamic context separation |
| **Verification** | Spot-checking ("Does it seem to work?") | Deterministic Pytest suites + LM Trajectory Evals |
| **Error Handling** | Copy-pasting error logs back to LLM | Self-diagnosing agents bounded by CI/CD quality gates |
| **Economics** | Low CapEx, High OpEx (high token burn & maintenance tax) | High CapEx, Low OpEx (75% token burn reduction, fast ROI crossover) |

---

## 🚧 Key Challenges & Solutions

### Challenge 1: Transitioning from Ad-Hoc Prompting to System Harnesses
- **The Issue**: Unstructured prompting creates "prompting loops" where agents burn API tokens attempting to fix unverified mistakes, leading to low first-pass success rates (40-50%) and high maintenance debt.
- **Solution**: Built the **Factory Model Engine** (`app/generator.py`). Demo Factory automatically scaffolds a production-grade repository harness:
  - **Static Context**: `AGENTS.md` enforcing system roles, stack rules, and hard boundaries.
  - **Dynamic Context**: Agent Skills (`.agent/skills/`) loaded on demand to prevent prompt rot.
  - **Automated Verification**: Pytest unit tests + JSON Trajectory Rubrics.

---

### Challenge 2: Cloud Deployment Payload Limit (< 8MB Footprint)
- **The Issue**: Google Vertex AI Reasoning Engine enforces a strict **8MB size limit** on deployment payloads. Packaging node_modules, static web assets, or heavy datasets inside the backend staging directory causes cloud deployment failure.
- **Solution**: Applied **Pattern A Decoupled Architecture**:
  - The staging backend (`app/` or `agent_engine/`) strictly contains `agent.py`, `models.py`, and minimal requirements.
  - Presentation assets are isolated in `static/` and mounted dynamically, ensuring staging payloads remain `< 2MB`.

---

### Challenge 3: Offline Sales Demo Resilience & Credential Friction
- **The Issue**: Customer Engineers often demonstrate agent solutions at customer sites or offline where active GCP credentials, live BigQuery datasets, or enterprise network connections are unavailable.
- **Solution**: Implemented **Dual-Mode Serving Architecture** (`app/simulation.py`):
  - **Online Mode**: Executes live Gemini 2.5/3.5 calls with OpenTelemetry tracing when GCP credentials exist.
  - **Offline Simulation Mode**: High-fidelity mock database and log engine that returns realistic agent responses, thoughts, tool calls, and eval scores with zero GCP configuration required.

---

### Challenge 4: Reserved Environment Variables & SDK Compatibility Gotchas
- **The Issue**:
  1. Vertex AI runtimes reject custom deployments specifying reserved environment variables like `GOOGLE_CLOUD_PROJECT` or `PORT`.
  2. Python environments running socket mutations crash on `pyOpenSSL` versions `>=26.2.0`.
  3. ADK entrypoint object discovery fails if the root agent instance is not named correctly.
- **Solution**:
  - Enforced unreserved mapping: `GCP_PROJECT` instead of `GOOGLE_CLOUD_PROJECT`.
  - Forced dependency pinning in `pyproject.toml`: `pyopenssl==24.3.0` and `cryptography==44.0.3`.
  - Mandated that the ADK export entrypoint variable in `app/agent.py` MUST be named `root_agent` or `app`.

---

### Challenge 5: Quantifying Business ROI for Engineering Leadership
- **The Issue**: CTOs and Engineering Managers often resist upfront spec and harness engineering due to perceived higher setup cost.
- **Solution**: Built an interactive **CapEx vs. OpEx TCO Calculator** based on Figure 9 in the paper:
  - Demonstrates that spending $4,000 upfront on harness design cuts monthly token burn by 75% and eliminates maintenance tax.
  - Calculates exact ROI crossover points (typically **< 1 month**).

---

### Challenge 6: Enterprise Workspace OAuth & Google Slides API Gotchas
- **The Issue**:
  1. Drive API `export()` method (`service.files().export(mimeType="text/plain")`) works for Docs/Sheets but returns HTTP 400 when called on Google Slides (`application/vnd.google-apps.presentation`).
  2. Tokens issued with `drive.apps.readonly` are rejected by Google Drive API (`SCOPE_NOT_PERMITTED`).
- **Solution**:
  - Integrated `Google Slides API v1` (`slides.v1`) to parse slide elements, text boxes, and titles into structured Markdown.
  - Enforced `https://www.googleapis.com/auth/drive.readonly` scope requirement and formatted detailed HttpError scope diagnostic messages in the UI.

---

## 📋 Best Practices & Engineering Checklist for New Demos

When creating any new agentic demo project, ensure compliance with the following checklist:

- [x] **Static Context**: Create `AGENTS.md` at repo root detailing tech stack, conventions, and hard rules.
- [x] **ADK Naming**: Export `root_agent` or `app` in `app/agent.py`.
- [x] **Crypto Pinning**: Pin `pyopenssl==24.3.0` and `cryptography==44.0.3` in `requirements.txt`.
- [x] **Env Security**: Use `GCP_PROJECT` instead of reserved `GOOGLE_CLOUD_PROJECT`.
- [x] **Workspace APIs**: Use `slides.v1` for Google Slides presentation parsing; require `drive.readonly` scope.
- [x] **Offline Resilience**: Provide high-fidelity simulation fallbacks in `app/simulation.py`.
- [x] **Deterministic Tests**: Include `pytest` unit tests in `tests/test_agent.py`.
- [x] **Trajectory Evals**: Include `app/eval_runner.py` to score trajectory compliance & LM rubrics.
- [x] **CI/CD Quality Gate**: Create `.github/workflows/ci.yml` gating PR merges on test & eval pass.
- [x] **Git Cleanliness**: Include `.gitignore` excluding `.venv/`, `__pycache__`, and `mock_sre_logs.json`.

