# ADK Agent Engine + OAuth — Google Drive Reader Demo

Scaffolded & Upgraded by **Demo Factory** following Agentic Engineering SDLC standards.

A production-ready ADK agent deployed on **Vertex AI Agent Engine** with **OAuth 2.0** support for reading Google Drive files (Docs, Sheets, Slides, CSV, text) on behalf of authenticated users. Supports dual-mode execution (Live GCP/ADK & High-Fidelity Offline Simulation).

---

## 🏛️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        TWO MODES OF OPERATION                   │
├────────────────────────────┬────────────────────────────────────┤
│     LOCAL / PRESENTATION   │         PRODUCTION                 │
│                            │                                    │
│  User (Browser)            │  User (Browser)                    │
│    ↓                       │    ↓                               │
│  Glassmorphism Web UI      │  Gemini Enterprise UI              │
│    ↓                       │    ↓                               │
│  FastAPI Backend / ADK     │  Gemini Enterprise OAuth Flow      │
│  (uses auths.py config)    │  (uses registered auth resource)   │
│    ↓                       │    ↓                               │
│  negotiate_creds()         │  Token injected into               │
│  Stage 2 → Stage 3         │  tool_context.state["temp:<ID>"]   │
│    ↓                       │    ↓                               │
│  Google Drive API / Sim    │  negotiate_creds()                 │
│                            │  Stage 1 (finds injected token)    │
│                            │    ↓                               │
│                            │  Google Drive API                  │
└────────────────────────────┴────────────────────────────────────┘
```

---

## 🔑 Three-Stage OAuth Negotiation (`negotiate_creds`)

| Stage | Mechanism | Environment |
|:---|:---|:---|
| **Stage 1** | Check `tool_context.state` for cached or injected token (`temp:<AUTH_ID>`) | **Production (Gemini Enterprise)** & cached local runs |
| **Stage 2** | Check `tool_context.get_auth_response()` for completed OAuth exchange | **Local ADK Web UI** |
| **Stage 3** | Call `tool_context.request_credential()` to trigger user consent | **Local ADK Web UI** |

---

## 🚀 Quick Start

### 1. Installation & Environment Setup
```bash
make setup
```

### 2. Run Presentation Dashboard
```bash
make run
```
Access UI at: `http://127.0.0.1:8080`

### 3. Register OAuth for Production Deployment (Optional)
```bash
make register-oauth
```

---

## 🧪 Testing & Evaluation Harness

```bash
make test  # Deterministic Pytest suite
make eval  # Non-deterministic Trajectory & LM Rubric Evals
```
