# Executive Pitch Deck Outline: The Enterprise Coding Harness

> **Target Audience**: CTOs, Heads of Engineering, Platform Architects, and Field CEs  
> **Theme**: Moving Beyond Model Hype to Enterprise Agent Infrastructure ($\text{Agent} = \text{Model} + \text{Harness}$)

---

## Slide 1: Title & Positioning
- **Title**: The Enterprise Agent Harness: How Gemini Enterprise Turns Models into Engineers
- **Subtitle**: Moving from brittle prompt wrappers to deterministic, stateful agent infrastructure.
- **Presenter**: Tony Ruiz | Specialist Customer Engineer / Advanced Agentic Coding

---

## Slide 2: The Industry Dilemma — The 80% Chasm
- **Headline**: Frontier Models are Everywhere. Production Agents are Not.
- **Data Point**: Over 80% of enterprise coding agent pilots stall in "demo purgatory."
- **Key Insight**: Models are reasoning engines, not operating systems. A model without a harness:
  - Hallucinates repo conventions.
  - Burns tokens dumping massive files instead of inspecting symbols.
  - Edits code blindly without syntax validation.
  - Pollutes production branches with broken intermediate state.

---

## Slide 3: The Thesis — $\text{Agent} = \text{Model} + \text{Harness}$
- **Visual**: Two halves of a cohesive architecture:
  - **Left (Model)**: Reasoning, planning, code generation (Commoditized, rapidly evolving, swappable).
  - **Right (Harness)**: Tools, memory, sessions, guardrails, and verification loops (Durable, proprietary, enterprise-controlled).
- **Core Message**: You don't build a durable business on prompt engineering; you build it on your **Harness**.

---

## Slide 4: Open-Source Friction vs. Enterprise Reality
- **Open-Source Trend**: Tools like Oh-my-pi (`omp`) and Pi prove that developers crave terminal harnesses (LSP, debuggers, worktrees).
- **The Catch**:
  - Complex custom CLI binaries that are hard to audit.
  - Fragile mechanisms like "hash-anchored edits" that models struggle to compute.
  - Lack of enterprise IAM, centralized memory, and zero-trust egress.
- **The Gemini Enterprise Answer**: We deliver this exact harness as a managed, secure, cloud-scale platform.

---

## Slide 5: The 5 Pillars of the Gemini Enterprise Coding Harness
1. **Prewalk Grounding**: ADK lifecycle callbacks dynamically ground the agent in workspace Git state and **Vertex AI Memory Bank** before token generation starts.
2. **In-Process Language Server Protocol (LSP)**: AST-aware symbol lookup and call graph tracing (90% token reduction vs. file dumps).
3. **Subagent Worktree Sandboxing**: Safe parallel refactoring in ephemeral Git worktrees; production branches remain pristine.
4. **Closed-Loop Verification**: Automated AST parsing and DAP test execution intercept errors before commits are made.
5. **Session Branching & Memory Consolidation**: Full trajectory tree with instant rewind, plus cross-session learning consolidation in **Memory Bank**.

---

## Slide 6: Architecture Diagram
- [Insert ADK + Gemini Enterprise Architecture Diagram from README.md]
- Show data flow between Developer IDE $\leftrightarrow$ ADK Harness on Cloud Run $\leftrightarrow$ Gemini 3.8 Flash $\leftrightarrow$ Memory Bank / Session Manager.

---

## Slide 7: Live Demonstration (The 3-Act Proof: Baseline -> Hill-Climb -> Victory)
- **Executive Demo Runner**: [`run_narrative_demo.py`](file:///usr/local/google/home/tonyruiz/Desktop/demos/jetski/demos/demo-factory/demos/gemini-enterprise-coding-harness/run_narrative_demo.py)  
- **Presenter Talk Track & Script**: [`DEMO_NARRATIVE_SCRIPT.md`](file:///usr/local/google/home/tonyruiz/Desktop/demos/jetski/demos/demo-factory/demos/gemini-enterprise-coding-harness/DEMO_NARRATIVE_SCRIPT.md)
- **Live 3-Act Storyboard**:
  1. **Act 1: The Baseline Struggle**: Run baseline harness against 8 real enterprise tasks; witness AST syntax errors, token blowouts, and a 37.5% baseline pass rate.
  2. **Act 2: Autonomous Hill-Climber in Action**: Launch Bayesian sequential early stopping (pruning a bad candidate in 3 steps, saving 62.5% compute); cluster failure traces into error archetypes; auto-mutate harness with AST verification & Memory Bank grounding.
  3. **Act 3: Re-Evaluation & Proven Generalization**: Candidate B achieves $P \ge 0.95$ early acceptance; passes the quarantined McNemar holdout test ($p < 0.05$); pass rate surges to 87.5% with 63% token savings.

---

## Slide 8: Business Value & ROI
- **Token Efficiency**: 70–85% reduction in context token costs by using targeted LSP tools over naive file chunking.
- **Zero Rework**: Closed-loop verification ensures zero syntactically broken commits reach CI/CD.
- **Knowledge Retention**: Memory Bank retains developer conventions across team onboarding, reducing senior engineer review fatigue.

---

## Slide 9: Getting Started
- Deploy the starter scaffold: `demos/gemini-enterprise-coding-harness`
- Connect your GitHub / GitLab repository.
- Schedule a 1-day Architecture Workshop with Google Cloud Customer Engineering.
