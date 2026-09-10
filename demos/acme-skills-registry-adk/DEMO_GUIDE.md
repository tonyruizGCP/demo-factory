# Presentation & Demo Script: Skill Registry with Custom ADK Agent
**Presenter**: Tony Ruiz, Google Cloud AI Specialist Customer Engineer  
**Audience**: ACME Inc Engineering & Data Science Leadership Team  
**Estimated Time**: 15–20 minutes  

---

## 🎯 Demo Objectives
1. **Validate ACME's Architectural Vision**: Affirm that their instinct to avoid creating separate agents per use case is spot-on, and showcase how Google Cloud's **Hub-and-Spoke Pattern** achieves this natively.
2. **Demonstrate Gemini Enterprise Skill Registry**: Show how skills are packaged as open, standard `agentskills.io` archives (`SKILL.md`, references, deterministic calculation scripts).
3. **Showcase Live ADK Integration**: Demonstrate the central `Retail Data Analyst` ADK agent discovering, dynamically loading, and executing skills on the fly.
4. **Answer the Beta Question**: Outline the exact onboarding steps, IAM roles, and timeline for ACME Inc to enable this in their GCP environment today.

---

## 🎙️ Step-by-Step Presentation Script

### Part 1: Setting the Stage (2 Minutes)
> *"Team, first off—your architectural intuition is 100% aligned with how Google Cloud designed the Gemini Enterprise Agent Platform. A lot of enterprise teams fall into what we call the 'Agent Proliferation Trap'—creating one agent for Store Reviews, another for Morning Recaps, another for Inventory Audits, each with duplicate copies of data access code and standing compute.*
> 
> *Today, I want to show you how our new **Skill Registry** combined with **ADK 2.x** allows you to keep **one central, heavy-lifting Retail Data Analyst Agent**, while distributing lightweight, versioned **Skills** directly to store managers and regional teams."*

---

### Part 2: The Skill Registry Architecture (3 Minutes)
Open `dashboard/static/index.html` (or `http://localhost:8080`).

1. **Highlight the Left Panel (Enterprise Skill Registry)**:
   > *"Notice the left sidebar. We have three skills published to the Google Cloud Skill Registry in `us-central1`: `store-performance-review`, `daily-summary-recap`, and `inventory-optimization-audit`.*
   > *Each skill follows the `agentskills.io` open standard. Click 'View SKILL.md Spec'. You'll see it contains structured markdown instructions, reference rubrics, and embedded Python calculation scripts like `calculate_store_kpis.py`."*

2. **Key Takeaway for ACME's Data Science Team**:
   > *"Because the skills live in the registry, your business analysts and merchandising managers can author new skills or adjust margin benchmarks without needing an engineering pull request to redeploy the core agent service."*

---

### Part 3: Live Agent Execution — Frontline Store Manager (5 Minutes)
1. **Scenario 1: Store Performance Diagnostic**:
   - Set Persona to **Store Manager**.
   - Select **Store #104 - Downtown Chicago Flagship**.
   - Click the quick query button: **"Run a store performance review for Store #104"**.

2. **Walk through the Right Panel (Real-Time ADK Trace)**:
   > *"Watch what happens in the ADK Execution Trace on the right in real time:*
   > - *Step 1: The agent receives the prompt.*
   > - *Step 2: Through `SkillToolset`, the agent calls `search_skills('store performance')` and discovers `store-performance-review`.*
   > - *Step 3: The agent invokes `load_skill` to dynamically ingest the procedural rules into its context.*
   > - *Step 4: The agent queries your underlying BigQuery warehouse via `query_store_sales`.*
   > - *Step 5: The agent executes the bundled `calculate_store_kpis.py` script inside its isolated sandbox, calculating conversion rate (25.63%) and labor efficiency ($219.31/hr) deterministically without hallucination!*
   > - *Step 6: It formats the final scorecard according to the skill's exact rubric."*

3. **Scenario 2: Morning Floor Supervisor Recap**:
   - Switch persona to **Assistant Store Manager** or select **Store #208 (West Suburbs)**.
   - Click: **"Generate yesterday's daily summary recap for morning huddle"**.
   > *"Notice how the same central agent seamlessly shifts from a deep financial analysis to a punchy, 3-minute morning briefing with zero code changes. It dynamically loaded `daily-summary-recap`, checked yesterday's pacing, identified critical out-of-stock items, and delivered 3 concrete floor directives."*

---

### Part 4: How ACME Inc Onboards Today (3 Minutes)
Show `README.md` Section 5.
> *"To answer your question on Beta access:*
> 1. *The Skill Registry API is actively deployed in `us-central1` under `aiplatform.googleapis.com` and `agentregistry.googleapis.com`.*
> 2. *ADK 2.5+ natively includes `SkillToolset` and `GCPSkillRegistry` out of the box.*
> 3. *Your team can start right now by granting `roles/agentregistry.admin` to your developers and adding `SkillToolset(registry=...)` to your existing `retail_data_analyst` agent code.*
> 4. *I can partner with you next week to pair-program on your first production skill upload."*
