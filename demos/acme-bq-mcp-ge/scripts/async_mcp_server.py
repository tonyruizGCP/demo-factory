#!/usr/bin/env python3
"""
Acme Asynchronous BYO-MCP Server (FastMCP / StreamableHTTP)
Deploys on Cloud Run. Handles long-running BigQuery analytical jobs
asynchronously to prevent Gemini Enterprise chat UI timeouts while maintaining MCP compliance.
"""

import os
import time
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from google.cloud import bigquery
from mcp.server.fastmcp import FastMCP
import uvicorn

load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "truiz-agy-demo")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "acme_media_intelligence")
BQ_LOCATION = os.getenv("BQ_LOCATION", "US")

# Initialize FastMCP Server with stateless HTTP support for Gemini Enterprise
mcp = FastMCP(
    name="acme-async-bq-mcp",
    instructions="Acme Corp Media Intelligence & Long-Running BigQuery Analytics MCP Server for Gemini Enterprise."
)
mcp.settings.stateless_http = True
mcp.settings.json_response = True
mcp.settings.transport_security.enable_dns_rebinding_protection = False

bq_client = bigquery.Client(project=GCP_PROJECT_ID, location=BQ_LOCATION)

@mcp.tool(
    name="submit_media_analysis_job",
    description="Submits a long-running BigQuery query or heavy media intelligence analysis job asynchronously without blocking.",
    annotations={"readOnlyHint": True, "destructiveHint": False}
)
async def submit_media_analysis_job(query_sql: str) -> Dict[str, Any]:
    """
    Submits a query asynchronously to BigQuery and immediately returns the Job ID.
    """
    try:
        job = bq_client.query(query_sql)
        return {
            "job_id": job.job_id,
            "status": "RUNNING",
            "created_at": job.created.strftime("%Y-%m-%d %H:%M:%S UTC") if job.created else str(time.time()),
            "message": f"Query submitted successfully. Job ID: {job.job_id}. Use check_job_status or fetch_job_results to retrieve output."
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "error_message": str(e)
        }

@mcp.tool(
    name="check_job_status",
    description="Checks the current execution status, state, and bytes processed of an asynchronous BigQuery job.",
    annotations={"readOnlyHint": True, "destructiveHint": False}
)
async def check_job_status(job_id: str) -> Dict[str, Any]:
    """
    Checks the status of an ongoing or completed BigQuery job.
    """
    try:
        job = bq_client.get_job(job_id)
        is_done = job.done()
        
        response = {
            "job_id": job_id,
            "state": job.state,  # PENDING, RUNNING, DONE
            "is_done": is_done,
            "total_bytes_processed": job.total_bytes_processed or 0,
            "error_result": job.error_result
        }
        if job.ended and job.started:
            response["duration_seconds"] = (job.ended - job.started).total_seconds()
        return response
    except Exception as e:
        return {"status": "ERROR", "error_message": str(e)}

@mcp.tool(
    name="fetch_job_results",
    description="Retrieves the final formatted results from a completed BigQuery query job.",
    annotations={"readOnlyHint": True, "destructiveHint": False}
)
async def fetch_job_results(job_id: str, max_rows: int = 100) -> Dict[str, Any]:
    """
    Fetches the result rows from a completed BigQuery job.
    """
    try:
        job = bq_client.get_job(job_id)
        if not job.done():
            return {
                "status": job.state,
                "message": f"Job {job_id} is still in state '{job.state}'. Please check back shortly."
            }
        
        if job.error_result:
            return {
                "status": "FAILED",
                "error": job.error_result
            }

        rows = [dict(row) for row in job.result(max_results=max_rows)]
        return {
            "status": "SUCCESS",
            "job_id": job_id,
            "row_count": len(rows),
            "rows": rows
        }
    except Exception as e:
        return {"status": "ERROR", "error_message": str(e)}

@mcp.tool(
    name="execute_quick_query",
    description="Executes a fast, interactive read-only BigQuery query synchronously (max 30s timeout).",
    annotations={"readOnlyHint": True, "destructiveHint": False}
)
async def execute_quick_query(query_sql: str, max_rows: int = 50) -> Dict[str, Any]:
    """
    Executes a fast query synchronously for interactive conversational grounding.
    """
    try:
        query_job = bq_client.query(query_sql)
        results = query_job.result(timeout=30.0)
        rows = [dict(row) for row in results]
        return {
            "status": "SUCCESS",
            "total_rows": len(rows),
            "rows": rows[:max_rows]
        }
    except Exception as e:
        return {"status": "ERROR", "error_message": str(e)}

@mcp.tool(
    name="list_available_tables",
    description="Lists all tables available in the default Acme media intelligence dataset.",
    annotations={"readOnlyHint": True, "destructiveHint": False}
)
async def list_available_tables() -> Dict[str, Any]:
    """
    Lists tables in the dataset.
    """
    try:
        dataset_ref = bigquery.DatasetReference(GCP_PROJECT_ID, BQ_DATASET_ID)
        tables = list(bq_client.list_tables(dataset_ref))
        table_ids = [t.table_id for t in tables]
        return {
            "dataset_id": BQ_DATASET_ID,
            "tables": table_ids
        }
    except Exception as e:
        return {"status": "ERROR", "error_message": str(e)}

# Create the Starlette Streamable HTTP App
app = mcp.streamable_http_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    print(f"🚀 Starting Acme Async FastMCP Server on port {port} over StreamableHTTP (/mcp)...")
    uvicorn.run(app, host="0.0.0.0", port=port)
