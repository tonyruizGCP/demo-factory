# 🏭 Demo Factory - Agentic Engineering & SDLC Generator

**Demo Factory** is an enterprise-grade agent generation and SDLC harness system built for Google Cloud Customer Engineers and AI Architects. Given a **Customer Use Case** (e.g., *E-Commerce Refund Assistant*, *AI SRE Incident Remediation*) and a **Technological Approach** (e.g., *ADK 2.0 + FastAPI + MCP*, *Multi-Agent Orchestrator + Guardrails*), Demo Factory generates a production-ready, fully verified demo project that adheres to GitHub/Git SDLC best practices.

Derived from the whitepaper:
> **"The New SDLC With Vibe Coding: From ad-hoc prompting to Agentic Engineering"** (Osmani, Saboo, & Kartakis, May 2026).

---

## ✨ Key Features

1. **Factory Model Engine**: Moves development from ad-hoc prompt tweaking ("Vibe Coding") to disciplined **Agentic Engineering** by generating the system that builds, tests, and verifies code.
2. **Context Engineering Architecture**:
   - **Static Context**: Generates customized `AGENTS.md` and repository guardrails.
   - **Dynamic Context**: Configures modular Agent Skills (`.agent/skills/`) for on-demand procedural knowledge.
3. **Decoupled Architecture**:
   - Lightweight Staging backend (`< 8MB` payload limit for Vertex AI Reasoning Engine).
   - High-fidelity Glassmorphism Web UI presentation.
4. **Dual-Mode Execution**:
   - **Online Mode**: Live Gemini / Vertex AI execution with OTel tracing.
   - **Offline Simulation Mode**: High-fidelity mock registry for offline sales demos with zero GCP setup required.
5. **Quality Gates & CI/CD Flywheel**:
   - Deterministic test suites (`pytest`).
   - Non-deterministic trajectory & output evaluations (`eval_suite.json` + LM judges).
   - GitHub Actions workflow (`.github/workflows/ci.yml`) enforcing security scanning and pre-commit verification.
6. **CapEx vs OpEx TCO Calculator**: Built-in economics calculator demonstrating token burn reduction and maintenance savings achieved by Agentic Engineering over unstructured vibe coding.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- `pip` or `uv`

### 2. Installation & Setup

```bash
cd demos/demo-factory
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the Demo Factory Dashboard

```bash
make run
# or
python3 -m app.main
```

Open your browser to: `http://127.0.0.1:8080`

---

## 🏛️ SDLC Harness Structure of Generated Demos

When Demo Factory scaffolds a project, it generates the following git/github best-practice structure:

```
generated-demo/
├── AGENTS.md                   # Static context & operational boundaries
├── README.md                   # Setup guide and architecture overview
├── pyproject.toml              # Dependency specs with pinned crypto packages
├── requirements.txt            # Staging requirements (<8MB deployment footprint)
├── Makefile                    # Standardized lifecycle commands (test, eval, run)
├── .github/
│   └── workflows/
│       └── ci.yml              # Quality gate: pytest + eval suite + security check
├── app/
│   ├── agent.py                # ADK root_agent definition
│   ├── main.py                 # FastAPI microservice
│   └── simulation.py           # Offline fallback simulation registry
├── tests/
│   ├── test_agent.py           # Deterministic test suite
│   └── test_evals.py           # Trajectory and LM judge evaluation harness
└── static/
    ├── index.html              # Customer-facing presentation UI
    ├── css/style.css           # Glassmorphism styling
    └── js/app.js               # Event polling and visual stream parser
```

---

## 📚 References & Best Practices
- **Vibe Coding to Agentic Engineering Whitepaper**: [vibecoding.pdf](file:///usr/local/google/home/tonyruiz/Desktop/demos/jetski/knowledge-vault/obsidian-jetski/sources/vibecoding.pdf)
- **ADK & FastAPI Demo Synthesis**: [adk-fastapi-demo-patterns.md](file:///usr/local/google/home/tonyruiz/Desktop/demos/jetski/knowledge-vault/obsidian-jetski/wiki/syntheses/adk-fastapi-demo-patterns.md)
- **ADK Demo Lessons & Standards**: [SKILL.md](file:///usr/local/google/home/tonyruiz/Desktop/demos/jetski/.agent/skills/adk-demo-lessons/SKILL.md)
