# Engineering & Architecture Learnings: OmniCommerce Managed Agents E-Commerce Demo

**Author:** Tony Ruiz, Google Cloud Customer Engineer (AI)  
**Project:** Unified Commerce Agent ("Omni-AI") Demo  
**Technology:** Google Cloud Managed Agents API (Vertex AI), FastAPI, GCS, Vanilla JS/CSS  

---

## 1. Managed Agents Environment Lifecycle & GCS Source Mounting

### 🧠 The Core Insight
In the Vertex AI Managed Agents API, environment configurations operate across two levels:
* **Agent Level (`base_environment`)**: Declared during `POST /agents`. Defines default sandbox specifications including mounted Google Cloud Storage (GCS) `sources`, network access allowlists, and base image specifications.
* **Interaction Level (`environment` in `POST /interactions`)**: Declared per-turn. Used for multi-turn session persistence or inline environment overrides.

### ⚠️ Gotcha: Overriding `base_environment`
If an interaction request explicitly passes:
```json
"environment": { "type": "remote" }
```
without re-specifying the `sources` array or providing a valid `env_id`, **the Managed Agents runtime provisions a fresh, empty remote container**, overriding all `sources` configured in `base_environment`. This caused the agent to report an empty `/workspace` directory.

### ✅ Solution & Best Practice
* **Inherit `base_environment`**: Omit the `environment` field in `POST /interactions` unless passing an existing session ID (`"env_id": "env_..."`).
* **Explicit GCS Mapping**: Mount GCS directories explicitly to subfolders:
  ```json
  "base_environment": {
    "type": "remote",
    "sources": [
      {"type": "gcs", "source": "gs://<bucket>/merchant_data", "target": "merchant_data"},
      {"type": "gcs", "source": "gs://<bucket>/skills", "target": "skills"}
    ]
  }
  ```

---

## 2. Event Stream Dissection: Disentangling Thoughts vs. Final Output

### 🧠 The Core Insight
Vertex AI Managed Agents stream SSE events for every step in the agent execution loop:
* `step.start`: Emits the step metadata (`step.type`: `"model_output"`, `"function_call"`, or `"function_result"`).
* `step.delta`: Emits text fragments (`delta.text`) or tool call arguments (`delta.arguments`).
* `step.stop`: Marks the completion of a step.

### ⚠️ Gotcha: Bundling Reasoning with Output
By default, standard Gemini text streaming concats all `delta.text` fragments. In an agentic setting, this bundles the model's inner monologue (e.g., *"I will list the contents of the workspace to check for catalog.json..."*) together with the final customer-facing response, producing a cluttered, repetitive experience for users.

### ✅ Solution & Best Practice
* **Step Classification**:
  * **Thoughts / Reasoning**: Text deltas emitted during model planning or preceding tool calls are flagged as `type: "thought"`.
  * **Tool Execution Traces**: Function call arguments and execution logs are flagged as `type: "trace_code"`.
  * **Final Output**: Text deltas emitted during the final answer step (after tool executions complete) are flagged as `type: "content"`.

---

## 3. UI/UX Patterns for Agentic Applications

### 🧠 The Core Insight
Enterprise users demand two things simultaneously:
1. **Clean, direct answers** (formatted emails, inventory status tables, ticket JSONs).
2. **Transparency and auditability** into how the AI arrived at its conclusions.

### ✅ Solution: Collapsible "Agent Reasoning & Tool Traces" Accordion
* **Default State**: Keep inner monologue and execution traces collapsed under a styled **"🧠 Agent Reasoning & Tool Traces"** toggle button.
* **Final Output**: Render the final response prominently in a primary response container with full GitHub-flavored Markdown support.
* **Auditability**: Users or engineers can click the toggle anytime to inspect the step-by-step thinking narration and tool execution logs.

---

## 4. Summary of API Endpoints & Configuration Reference

| Feature | REST Endpoint | Key Payload Note |
|---|---|---|
| **Agent Registration** | `POST /v1beta1/projects/{P}/locations/{L}/agents` | Define `base_environment` with `sources` |
| **Agent Deletion** | `DELETE /v1beta1/projects/{P}/locations/{L}/agents/{id}` | Forces container teardown & refresh |
| **Submit Interaction** | `POST /v1beta1/projects/{P}/locations/{L}/interactions` | Set `background: true`, `stream: true`, omit `environment` to inherit `base_environment` |
| **List Workspace Files** | `GET /api/environment/workspace` | Returns file metadata & target paths in `/workspace` |
| **Read Workspace File** | `GET /api/environment/workspace/file?path=...` | Retrieves raw content of a workspace file |
| **List Environment Skills** | `GET /api/environment/skills` | Returns mounted GCS skills & master directive markdown |

---

## 5. Control Plane Environment & Workspace Inspection

### 🧠 The Core Insight
In production agentic architectures, developers and operations teams need live visibility into:
1. **Container Workspace Datasets**: Inspecting the raw state of files mounted under `/workspace/merchant_data/` (`catalog.json`, `orders.json`, `customers.json`, `tickets.json`).
2. **Mounted GCS Skills Directives**: Inspecting the system directives loaded under `/workspace/skills/` (`unified_commerce_skill.md`) alongside their remote GCS bucket URIs (`gs://<bucket>/skills/...`).

### ✅ Solution & Implementation
* Added Control Plane inspection endpoints:
  - `GET /api/environment/workspace`: Lists files, relative paths, container target paths, and file sizes.
  - `GET /api/environment/workspace/file?path=...`: Retrieves file contents for live preview in the Control Plane UI.
  - `GET /api/environment/skills`: Retrieves mounted skills, GCS source bucket mappings, and full directive Markdown content.
* Integrated a 4-card **Agent Control Plane & Environment Inspector** grid in the Web UI:
  - **Active Agent Config**: Resource ID, Base Model, System Instructions, Deploy status.
  - **Container Workspace Explorer**: Dropdown file selector and syntax-styled viewer for `/workspace/merchant_data/`.
  - **Mounted Environment Skills**: Target path, GCS URI, and master directive viewer.
  - **GCP Diagnostics Console**: OAuth2 credentials, project ID, location, and API status verification.
