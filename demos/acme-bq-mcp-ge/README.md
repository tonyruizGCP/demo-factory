# Acme Corp — BigQuery MCP & Gemini Enterprise (GE) Demo Suite

This repository provides a customer-ready demonstration and testing framework for integrating **Google Cloud BigQuery** with **Gemini Enterprise (GE)** using **Model Context Protocol (MCP)** connectors.

Designed for customer **Acme Corp**, this demo showcases:
1. **Interactive Conversational Grounding**: Natural language querying across enterprise media intelligence and brand telemetry.
2. **BYO MCP Connector Integration**: Adding BigQuery as a custom MCP Data Store in Gemini Enterprise with OAuth delegation.
3. **Asynchronous Long-Running Task Decoupling**: Handling multi-minute analytical queries without chat UI/gateway connection timeouts using Cloud Run FastMCP.

---

## 🏗️ Architecture Overview

```
                                  ┌─────────────────────────────────────────────────────────┐
                                  │                Gemini Enterprise App                    │
                                  │           (Interactive Web Chat Assistant)              │
                                  └───────────────┬─────────────────────────┬───────────────┘
                                                  │                         │
                        Synchronous tools/call    │                         │  Synchronous tools/call
                        (<3 min queries)          │                         │  (Decoupled Job Pattern)
                                                  ▼                         ▼
┌────────────────────────────────────────────────────────┐   ┌──────────────────────────────────────────────┐
│  Track 1: Native BigQuery Managed Remote MCP           │   │  Track 2: Acme Async BYO-MCP (Cloud Run)     │
│  Endpoint: https://bigquery.googleapis.com/mcp         │   │  Endpoint: https://acme-async-bq-mcp.run.app │
│  - list_dataset_ids, list_table_ids                    │   │  - submit_media_analysis_job (returns job_id)│
│  - get_table_info, execute_sql_readonly                │   │  - check_job_status (polls BQ Job/PubSub)    │
│  - Max: 3-min timeout, 3,000 rows                      │   │  - fetch_job_results (returns formatted data)│
└────────────────────────┬───────────────────────────────┘   └──────────────────────┬───────────────────────┘
                         │                                                          │
                         ▼                                                          ▼
                 BigQuery Datasets                                          BigQuery Async Jobs API
            `acme_media_intelligence`                                (Heavy Multi-TB & Long-Running Scans)
```

---

## 📁 Repository Structure

```
acme-bq-mcp-ge/
├── .env.example                       # Environment configuration template
├── requirements.txt                   # Python dependencies
├── Dockerfile                         # Cloud Run container definition for Async MCP
├── deploy_cloudrun.sh                 # Deployment script for Custom MCP on Cloud Run
├── README.md                          # Architecture & execution guide
└── scripts/
    ├── generate_and_push_dataset.py   # Synthesizes and loads media intelligence dataset in BigQuery
    ├── test_bq_queries.py             # Executes live analytical SQL queries & benchmarks latency
    ├── test_mcp_integration.py        # Validates MCP JSON-RPC protocol (tools/list, tools/call)
    ├── test_gemini_enterprise_app.py  # Tests conversational queries against GE App instance
    └── async_mcp_server.py            # FastMCP Cloud Run server with async job polling pattern
```

---

## ⚡ Quickstart Setup

### 1. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your Google Cloud Project details:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
GCP_PROJECT_ID=truiz-agy-demo
GCP_REGION=us-central1
BQ_LOCATION=US
BQ_DATASET_ID=acme_media_intelligence
GE_LOCATION=global
GE_APP_ID=acme-media-intelligence-app
GE_DATASTORE_ID=acme-bq-mcp-datastore
```

### 2. Generate & Push Dataset to BigQuery
Run the generator to create and seed the `acme_media_intelligence` tables in BigQuery:

```bash
python scripts/generate_and_push_dataset.py
```

### 3. Test Direct BigQuery Queries
Execute the benchmark test suite to verify data and performance:

```bash
python scripts/test_bq_queries.py
```

### 4. Deploy Custom Async MCP Server to Cloud Run
Build and deploy the FastMCP StreamableHTTP endpoint:

```bash
./deploy_cloudrun.sh
```

---

## 🔐 Comprehensive Authentication & OAuth 2.0 Configuration Guide

Setting up authentication for Custom MCP Connectors in Gemini Enterprise is the most critical step and often the primary source of configuration issues for developers.

### Step 1: Create an OAuth 2.0 Web Application Client in GCP
Gemini Enterprise utilizes **3-Legged OAuth (3LO) user delegation**. This ensures all BigQuery queries are executed under the identity and IAM permissions of the logged-in user, rather than using a static service account key.

1. Navigate to **Google Cloud Console** $\rightarrow$ **APIs & Services** $\rightarrow$ **Credentials**.
2. Click **Create Credentials** $\rightarrow$ **OAuth client ID**.
3. Select Application Type: **Web application**.
4. Set Name: `Gemini Enterprise Custom MCP Connector Client`.
5. Under **Authorized redirect URIs**, add the following exact URLs:
   ```
   https://vertexaisearch.cloud.google.com/oauth-callback
   https://discoveryengine.googleapis.com/oauth-callback
   ```
6. Click **Create** and securely record the generated:
   * **Client ID** (e.g., `442606385483-xxxx.apps.googleusercontent.com`)
   * **Client Secret** (e.g., `GOCSPX-xxxx`)

> [!IMPORTANT]
> Ensure the **OAuth Consent Screen** (under *APIs & Services $\rightarrow$ OAuth consent screen*) is configured for **Internal** (if within your Google Workspace domain) or has your test user accounts added under **Test users** (if External).

### Step 2: Configure Scopes
Ensure the OAuth client has permission to request the following scopes:
* `https://www.googleapis.com/auth/bigquery` (Access BigQuery data and run jobs)
* `https://www.googleapis.com/auth/userinfo.email` (User identity verification)
* `openid` (Standard OpenID Connect token verification)

### Step 3: Grant Cloud Run Service Account IAM Permissions
The Cloud Run service account requires permissions to interact with BigQuery and manage query execution:

```bash
PROJECT_ID="truiz-agy-demo"
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant BigQuery User role to run jobs
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/bigquery.user"

# Grant BigQuery Data Viewer role to inspect dataset schemas
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/bigquery.dataViewer"
```

---

## 🛠️ Critical Developer Challenges & "Gotchas"

### Gotcha 1: The "Blank / 0 Custom Actions" Discovery Issue
* **The Symptom**: When adding a new Custom MCP Server or the Managed BigQuery endpoint (`https://bigquery.googleapis.com/mcp`) in Gemini Enterprise Data Stores, the connector shows **0 tools / actions discovered**.
* **Root Cause**: The MCP server enforces OAuth 2.0 authentication. Until the user authenticates, the Gemini Enterprise client cannot execute the initial `tools/list` discovery RPC.
* **The Fix**:
  1. In the GCP Console, navigate to **Agent Builder / Discovery Engine** $\rightarrow$ **Data Stores**.
  2. Select your Custom MCP Data Store and go to the **Actions** tab.
  3. Click the blue **"Reload custom actions"** button.
  4. Complete the Google OAuth 2.0 popup and approve scopes.
  5. The page will reload displaying all discovered tools (`execute_sql_readonly`, `submit_media_analysis_job`, `check_job_status`, etc.) with checkboxes to enable.

---

### Gotcha 2: FastMCP DNS Rebinding Rejections (HTTP 400 Bad Request)
* **The Symptom**: Calls from Gemini Enterprise to your Cloud Run FastMCP endpoint fail with HTTP 400 or generic connection errors.
* **Root Cause**: FastMCP includes built-in DNS rebinding protection that rejects incoming HTTP requests when the `Host` header (`*.a.run.app`) doesn't match `localhost` or `127.0.0.1`.
* **The Fix**: Explicitly disable DNS rebinding protection in `async_mcp_server.py`:
  ```python
  mcp.settings.transport_security.enable_dns_rebinding_protection = False
  ```

---

### Gotcha 3: Stateless HTTP vs. Stateful SSE on Serverless Cloud Run
* **The Symptom**: `tools/call` requests fail intermittently or return session not found errors when Cloud Run scales out to multiple container instances.
* **Root Cause**: Traditional MCP implementations rely on long-lived SSE (Server-Sent Events) connections with stateful session IDs. Cloud Run distributes HTTP requests statelessly across instances.
* **The Fix**: Configure FastMCP for pure **StreamableHTTP** with stateless JSON responses:
  ```python
  mcp.settings.stateless_http = True
  mcp.settings.json_response = True
  ```

---

### Gotcha 4: Preventing the "What is your GCP project?" LLM Prompt Loop
* **The Symptom**: Even when the MCP server is connected, every user prompt in Gemini Enterprise triggers the model to ask: *"What is your GCP Project ID?"* or *"What is your BigQuery dataset?"*.
* **Root Cause**: The foundational model does not know the default project or dataset parameters unless provided in the system prompt.
* **The Fix**: Paste the structured instructions below directly into **Agent Designer $\rightarrow$ Instructions**.

---

## 🤖 Gemini Enterprise Agent Designer Instructions

To eliminate prompt friction, configure the **Agent Instructions** in the Gemini Enterprise Agent Designer:

```markdown
You are an enterprise data intelligence assistant for Acme Corp.
You have access to the Acme Media Intelligence BigQuery dataset via Model Context Protocol (MCP) tools.

Default Environment Settings:
- GCP Project: truiz-agy-demo
- Dataset: acme_media_intelligence
- Primary Tables: media_mentions, brand_competitors, campaign_performance, daily_sentiment_aggregates

Tool Usage Guidelines:
1. Always query the `truiz-agy-demo.acme_media_intelligence` dataset directly without asking the user for their project or dataset name.
2. For fast lookups and aggregations, use `execute_sql_readonly` or `execute_quick_query`.
3. For heavy long-running analytical queries, use `submit_media_analysis_job` to obtain a job_id, check status with `check_job_status`, and retrieve results with `fetch_job_results`.
4. Present findings with clear Markdown tables, percentage changes, and actionable business takeaways.
```
