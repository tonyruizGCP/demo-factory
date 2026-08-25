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

## 🤖 Gemini Enterprise Agent Designer Instructions

To optimize agent responses and eliminate repeated questions about GCP project or dataset IDs, paste the following into the **Agent Instructions** in the Gemini Enterprise Agent Designer:

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
