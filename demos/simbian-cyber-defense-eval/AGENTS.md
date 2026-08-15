# ACME AI Security Auditing & Threat Hunting Agent Specification

This reference specification defines the multi-agent architecture, specialist roles, model routing rules, and skill contracts for autonomous security auditing, vulnerability scanning, and Simbian Cyber Defense threat hunting.

---

## 1. System Architecture & Orchestrator

The harness operates as a hierarchical multi-agent team comprising **1 Lead Security Orchestrator** and **7 Weighted Specialist Sub-Agents**.

```
                           ┌────────────────────────────────────────────────┐
                           │          Lead Security Orchestrator            │
                           │  (Triage, Task Dispatching, Budget Control)    │
                           └───────────────────────┬────────────────────────┘
                                                   │
         ┌───────────────────┬─────────────────────┼─────────────────────┬───────────────────┐
         ▼                   ▼                     ▼                     ▼                   ▼
┌──────────────────┐┌──────────────────┐┌─────────────────────┐┌──────────────────┐┌──────────────────┐
│  Attack Surface  ││  Telemetry SQL   ││    CVE & Code       ││  MITRE ATT&CK    ││  Vulnerability   │
│     Mapping      ││     Analyst      ││     Analyzer        ││    Classifier    ││    Validator     │
│   (Weight: 1.0)  ││   (Weight: 1.2)  ││   (Weight: 1.1)     ││   (Weight: 1.3)  ││   (Weight: 1.2)  │
└──────────────────┘└──────────────────┘└─────────────────────┘└──────────────────┘└──────────────────┘
                                                   │
                                 ┌─────────────────┴─────────────────┐
                                 ▼                                   ▼
                      ┌──────────────────────┐            ┌──────────────────────┐
                      │    False Positive    │            │  Patch Remediation   │
                      │        Pruner        │            │      Generator       │
                      │     (Weight: 1.0)    │            │     (Weight: 0.9)    │
                      └──────────────────────┘            └──────────────────────┘
```

---

## 2. Multi-Agent Role Definitions & Skill Registry

| Agent Name | Skill ID | Weight | Primary Responsibility | Model / Thinking Budget |
| :--- | :--- | :---: | :--- | :--- |
| **Lead Security Orchestrator** | `orchestrator` | 1.5 | Incident intake, kill-chain hypothesis generation, sub-agent task routing, and execution termination. | Gemini 3.7 Flash (`budget: 2048`) |
| **Attack Surface Mapper** | `attack_surface_mapping` | 1.0 | Maps entry points, external network listeners, exposed APIs, and initial access vectors. | Gemini 3.7 Flash (`budget: 1024`) |
| **Telemetry SQL Analyst** | `telemetry_sql_analyst` | 1.2 | Formulates and executes SQL queries against raw SOC telemetry (processes, registry, sockets). | Gemini 3.7 Flash (`budget: 2048`) |
| **CVE & Code Analyzer** | `cve_code_analyzer` | 1.1 | Inspects source files, dependencies, and configuration artifacts for known vulnerability patterns. | Gemini 3.7 Flash (`budget: 1024`) |
| **MITRE ATT&CK Classifier** | `mitre_attack_classifier` | 1.3 | Maps telemetry and code anomalies to official MITRE Enterprise tactics and techniques. | Gemini 3.7 Flash (`budget: 2048`) |
| **Vulnerability Validator** | `vulnerability_validator` | 1.2 | Verifies exploitability in the Harbor sandbox environment and confirms parent-child process chains. | Gemini 3.7 Flash (`budget: 2048`) |
| **False Positive Pruner** | `false_positive_pruner` | 1.0 | Filters benign administrative activity, developer scripts, and non-exploitable alerts. | Gemini 3.7 Flash (`budget: 1024`) |
| **Patch Remediation Generator** | `patch_remediation_generator` | 0.9 | Authors defensive remediation patches, Sigma detection rules, and config fixes. | Gemini 3.7 Flash (`budget: 2048`) |

---

## 3. Operational Philosophy & Deterministic Guardrails

1. **Deterministic-First ("Zero Token") Rule**:
   - Initial triage and static regex/AST filtering execute deterministically without LLM calls.
   - LLM reasoning is invoked strictly for complex telemetry correlation, multi-stage kill-chain tracing, and exploit validation.
2. **Step Bounds & Token Budgeting**:
   - Investigations are capped at **4 to 6 discrete tool execution turns** to prevent unbounded agent loops.
   - Default `thinking_budget`: **2048 tokens** for deep reasoning, scalable up to **4096 tokens** for multi-stage APTs.
3. **Strict Vertex AI Perimeter**:
   - All model inference is constrained to Vertex AI (`us-central1`), with zero customer data retention for model retraining.
   - Telemetry databases execute inside isolated in-memory or containerized **Harbor Sandboxes** with outbound network egress blocked.
