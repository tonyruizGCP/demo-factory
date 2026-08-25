#!/usr/bin/env python3
"""
Acme MCP Integration Tester
Tests Model Context Protocol (MCP) StreamableHTTP JSON-RPC endpoints
(Google Managed BigQuery MCP Server or Custom Cloud Run Async Proxy).
"""

import os
import sys
import json
import httpx
from dotenv import load_dotenv
import google.auth
import google.auth.transport.requests

load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "truiz-agy-demo")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "acme_media_intelligence")
MCP_SERVER_URL = os.getenv("CUSTOM_MCP_SERVER_URL") or os.getenv("BQ_MCP_SERVER_URL", "https://bigquery.googleapis.com/mcp")

print(f"🚀 Initializing MCP Integration Test against: {MCP_SERVER_URL}")

# Get OAuth/ADC access token
try:
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/bigquery", "https://www.googleapis.com/auth/cloud-platform"])
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    access_token = credentials.token
    print("✅ Successfully acquired Google Cloud OAuth2 Access Token.")
except Exception as e:
    print(f"⚠️ Warning: Could not obtain ADC credentials: {e}")
    access_token = None

headers = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json"
}
if access_token and "bigquery.googleapis.com" in MCP_SERVER_URL:
    headers["Authorization"] = f"Bearer {access_token}"

def call_mcp(method: str, params: dict = None, request_id: int = 1):
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method
    }
    if params:
        payload["params"] = params
    
    print(f"\n👉 Calling MCP Method: `{method}`")
    with httpx.Client(timeout=30.0) as client:
        res = client.post(MCP_SERVER_URL, headers=headers, json=payload)
        print(f"   Status Code: {res.status_code}")
        try:
            body = res.json()
            return body
        except Exception:
            return {"raw_text": res.text}

def run_tests():
    # 1. Initialize
    init_res = call_mcp("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "acme-test-client", "version": "1.0"}
    }, 1)
    print("   Server Info:", init_res.get("result", {}).get("serverInfo"))

    # 2. List Tools
    tools_res = call_mcp("tools/list", {}, 2)
    tools = tools_res.get("result", {}).get("tools", [])
    print(f"   Discovered {len(tools)} tools:")
    for t in tools:
        print(f"   • {t['name']}: {t.get('description', '')[:70]}...")

    # 3. Call execute_sql_readonly or execute_quick_query
    print("\n" + "=" * 80)
    print("3. Executing Analytical Query via MCP Tool Call...")
    print("=" * 80)
    
    sample_sql = f"SELECT brand_name, COUNT(*) as mention_count, ROUND(AVG(sentiment_score), 3) as avg_sentiment FROM `{GCP_PROJECT_ID}.{BQ_DATASET_ID}.media_mentions` GROUP BY brand_name ORDER BY mention_count DESC"
    
    tool_names = [t["name"] for t in tools]
    if "execute_sql_readonly" in tool_names:
        call_params = {"name": "execute_sql_readonly", "arguments": {"projectId": GCP_PROJECT_ID, "query": sample_sql}}
    elif "execute_quick_query" in tool_names:
        call_params = {"name": "execute_quick_query", "arguments": {"query_sql": sample_sql}}
    else:
        call_params = {"name": tool_names[0], "arguments": {}}

    call_res = call_mcp("tools/call", call_params, 3)
    print("Tool Call Result:")
    print(json.dumps(call_res, indent=2))

if __name__ == "__main__":
    run_tests()
