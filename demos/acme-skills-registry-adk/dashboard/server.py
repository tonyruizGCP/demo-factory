# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Interactive Showcase Dashboard Server for ACME Retail Skills & ADK Agent."""

import asyncio
import json
import os
import pathlib
import subprocess
import sys
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add project root to sys.path
ROOT_DIR = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.agent import root_agent
from app.registry import get_skill_registry
from app.tools import MOCK_STORE_DATA, query_store_inventory, query_store_sales

app = FastAPI(
    title="ACME Retail: Agent Platform Skills Registry & ADK Showcase",
    description="Demonstrates consuming Gemini Enterprise Agent Platform skills within an ADK Agent."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = get_skill_registry()
STATIC_DIR = pathlib.Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    message: str
    store_id: str = "104"
    persona: str = "Store Manager"


@app.get("/api/registry/skills")
async def list_registry_skills():
    """Returns all registered skills in the enterprise catalog."""
    return {"skills": registry.list_all_skills()}


@app.get("/api/stores")
async def list_stores():
    """Returns ACME retail stores available for testing."""
    stores = []
    for sid, data in MOCK_STORE_DATA.items():
        stores.append({
            "id": sid,
            "name": data["name"],
            "region": data["region"],
            "format": data["format"],
            "manager": data["manager"]
        })
    return {"stores": stores}


@app.post("/api/agent/chat")
async def chat_with_agent(req: ChatRequest):
    """Executes the Retail Data Analyst agent workflow, simulating dynamic skill resolution."""
    user_query = req.message.lower()
    store_id = req.store_id.strip()

    # Step 1: Trace initialization
    trace: List[Dict[str, Any]] = [
        {
            "step": 1,
            "phase": "USER_INTENT_INGESTION",
            "title": "User Query Received",
            "detail": f"Persona: {req.persona} | Store: #{store_id} | Query: '{req.message}'"
        }
    ]

    # Step 2: Skill Discovery in Registry
    search_results = await registry.search_skills(query=req.message)
    matched_skill_name = "store-performance-review"
    if "daily" in user_query or "recap" in user_query or "huddle" in user_query or "yesterday" in user_query:
        matched_skill_name = "daily-summary-recap"
    elif "inventory" in user_query or "audit" in user_query or "stock" in user_query:
        matched_skill_name = "inventory-optimization-audit"

    trace.append({
        "step": 2,
        "phase": "SKILL_DISCOVERY",
        "title": "Querying Agent Platform Skill Registry",
        "tool": "search_skills",
        "args": {"query": req.message},
        "output": f"Found {len(search_results)} relevant skills. Selected target skill: '{matched_skill_name}'."
    })

    # Step 3: Dynamic Skill Ingestion
    skill = await registry.get_skill(name=matched_skill_name)
    trace.append({
        "step": 3,
        "phase": "SKILL_INGESTION",
        "title": f"Dynamic Loading: '{matched_skill_name}'",
        "tool": "load_skill",
        "args": {"skill_name": matched_skill_name},
        "output": f"Loaded SKILL.md ({len(skill.instructions)} bytes), scripts: {skill.resources.list_scripts()}, references: {skill.resources.list_references()}"
    })

    # Step 4: Execute Underling Data Tools
    sales_data = query_store_sales(store_id=store_id, date_range="yesterday" if matched_skill_name == "daily-summary-recap" else "last_30_days")
    inv_data = query_store_inventory(store_id=store_id)

    trace.append({
        "step": 4,
        "phase": "DATA_TOOL_EXECUTION",
        "title": "Calling Retail Data Tools",
        "tool": "query_store_sales",
        "args": {"store_id": store_id, "date_range": sales_data["reporting_period"]},
        "output": f"Retrieved sales: ${sales_data.get('gross_revenue', 0):,.2f} (Target: ${sales_data.get('target_budget', 0):,.2f}), foot traffic: {sales_data.get('foot_traffic', 0):,}"
    })

    # Step 5: Execute Skill-Bundled Script
    script_output = {}
    if matched_skill_name == "store-performance-review":
        script_path = ROOT_DIR / "skills" / "store-performance-review" / "scripts" / "calculate_store_kpis.py"
        cmd = [
            sys.executable, str(script_path),
            "--revenue", str(sales_data["gross_revenue"]),
            "--target", str(sales_data["target_budget"]),
            "--traffic", str(sales_data["foot_traffic"]),
            "--transactions", str(sales_data["transaction_count"]),
            "--labor_hours", str(sales_data["labor_hours"])
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            script_output = json.loads(proc.stdout)
            trace.append({
                "step": 5,
                "phase": "SKILL_SCRIPT_EXECUTION",
                "title": "Running Skill Automation Script",
                "tool": "run_skill_script",
                "args": {"skill_name": matched_skill_name, "file_path": "scripts/calculate_store_kpis.py"},
                "output": script_output
            })
    elif matched_skill_name == "daily-summary-recap":
        script_path = ROOT_DIR / "skills" / "daily-summary-recap" / "scripts" / "generate_huddle_brief.py"
        cmd = [
            sys.executable, str(script_path),
            "--sales", str(sales_data["gross_revenue"]),
            "--target", str(sales_data["target_budget"]),
            "--transactions", str(sales_data["transaction_count"])
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            script_output = json.loads(proc.stdout)
            trace.append({
                "step": 5,
                "phase": "SKILL_SCRIPT_EXECUTION",
                "title": "Running Skill Automation Script",
                "tool": "run_skill_script",
                "args": {"skill_name": matched_skill_name, "file_path": "scripts/generate_huddle_brief.py"},
                "output": script_output
            })
    else:
        script_path = ROOT_DIR / "skills" / "inventory-optimization-audit" / "scripts" / "audit_inventory.py"
        cmd = [
            sys.executable, str(script_path),
            "--total-skus", str(inv_data.get("total_skus", 100)),
            "--out-of-stock", str(len(inv_data.get("out_of_stock_skus", []))),
            "--low-stock", str(len(inv_data.get("low_stock_skus", [])))
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            script_output = json.loads(proc.stdout)
            trace.append({
                "step": 5,
                "phase": "SKILL_SCRIPT_EXECUTION",
                "title": "Running Skill Automation Script",
                "tool": "run_skill_script",
                "args": {"skill_name": matched_skill_name, "file_path": "scripts/audit_inventory.py"},
                "output": script_output
            })

    # Step 6: Generate Formatted Output following SKILL.md instructions
    if matched_skill_name == "store-performance-review":
        kpi = script_output
        variance_sign = "+" if kpi.get("variance_percent", 0) >= 0 else ""
        response_md = f"""# 🏬 ACME Retail Store Performance Review: Store #{store_id} ({sales_data['store_name']})

## 📊 Performance Scorecard
| Metric | Actual | Target / Benchmark | Status |
| :--- | :--- | :--- | :--- |
| **Gross Revenue** | ${kpi.get('revenue_actual', 0):,.2f} | ${kpi.get('revenue_target', 0):,.2f} | {kpi.get('evaluation_flags', {}).get('budget_status', '🟢 Healthy')} |
| **Budget Variance** | {variance_sign}{kpi.get('variance_percent', 0):.2f}% (${kpi.get('variance_dollars', 0):,.2f}) | 0.0% | {kpi.get('evaluation_flags', {}).get('budget_status', '🟢 Healthy')} |
| **Conversion Rate** | {kpi.get('conversion_rate_percent', 0):.2f}% | ≥ 24.5% | {kpi.get('evaluation_flags', {}).get('conversion_status', '🟢 Healthy')} |
| **Avg Order Value (AOV)** | ${kpi.get('average_order_value', 0):.2f} | $70.00 – $85.00 | 🟢 On Target |
| **Sales per Labor Hour** | ${kpi.get('sales_per_labor_hour', 0):.2f} / hr | ≥ $185.00 | {kpi.get('evaluation_flags', {}).get('labor_status', '🟢 Healthy')} |

## 🔍 Diagnostic Findings
- **Top Margin Driver**: **Apparel & Outerwear** generated ${sales_data['departments']['Apparel & Outerwear']['revenue']:,.2f} at **{sales_data['departments']['Apparel & Outerwear']['margin_pct']}%** gross margin.
- **Traffic vs. Conversion**: Store recorded **{sales_data['foot_traffic']:,}** visitors with a strong **{kpi.get('conversion_rate_percent', 0):.2f}%** shopper conversion rate.
- **Inventory Friction**: Detected **{len(inv_data.get('out_of_stock_skus', []))} critical stockouts** affecting peak categories (notably `{inv_data.get('out_of_stock_skus', [{}])[0].get('name', 'N/A')}`).

## 🎯 High-Impact Action Items (Next 7 Days)
1. **Floor Staffing Peak Alignment**: Maintain current labor scheduling density ({sales_data['labor_hours']} hrs) during 11:30 AM – 2:00 PM peak traffic windows.
2. **Stock Replenishment Transfer**: Expedite replenishment ticket for `{inv_data.get('out_of_stock_skus', [{}])[0].get('sku', 'N/A')}` from Midwest DC to recover estimated lost revenue.
3. **Cross-Merchandising**: Position footwear accessories adjacent to apparel fitting rooms to drive Units Per Transaction (UPT) above 2.8.
"""
    elif matched_skill_name == "daily-summary-recap":
        huddle = script_output
        variance_sign = "+" if huddle.get("variance_pct", 0) >= 0 else ""
        top_dept = max(sales_data["departments"].items(), key=lambda x: x[1]["revenue"])
        response_md = f"""# ☀️ Morning Store Huddle: Store #{store_id} ({sales_data['store_name']})

## ⚡ Yesterday's Flash Snapshot
- **Revenue**: ${huddle.get('sales', 0):,.2f} (Goal: ${huddle.get('target', 0):,.2f} | **{variance_sign}{huddle.get('variance_pct', 0)}%**)
- **Transactions**: **{huddle.get('transactions', 0)}** transactions @ **${huddle.get('aov', 0):.2f}** average basket.
- **Star Category**: **{top_dept[0]}** (${top_dept[1]['revenue']:,.2f} | {top_dept[1]['margin_pct']}% margin).
- **Pacing**: *{huddle.get('pacing_tone', 'On track!')}*

## 🚨 Inventory & Floor Alerts
- **Out of Stock**: `{inv_data.get('out_of_stock_skus', [{}])[0].get('name', 'None')}` is depleted. Guide customers to order via omnichannel kiosk.
- **Low Stock Warning**: `{inv_data.get('low_stock_skus', [{}])[0].get('name', 'None')}` has only {inv_data.get('low_stock_skus', [{}])[0].get('units_left', 0)} units left on floor display.

## 🎯 Shift Focus Directives
1. **Goal for Today**: Beat the daily plan (${huddle.get('target', 0):,.2f}) by pushing the {top_dept[0]} promotion.
2. **Floor Coverage**: Ensure designated coverage in high-traffic zones between 12 PM - 3 PM.
3. **Customer Greeting**: Target 100% greeting rate to keep customer conversion above 25%.
"""
    else:
        audit = script_output
        response_md = f"""# 📦 Inventory Health & Optimization Audit: Store #{store_id}

## 📊 Inventory Health Summary
- **Overall In-Stock Rate**: **{audit.get('in_stock_rate_pct', 0)}%** ({audit.get('inventory_health_rating', 'OPTIMAL')})
- **Total Tracked SKUs**: {audit.get('total_tracked_skus', 0):,}
- **Out-of-Stock SKUs**: {audit.get('out_of_stock_count', 0)}
- **Low-Stock Alerts**: {audit.get('low_stock_warning_count', 0)}

## 🚨 Critical Action Items
- **Automated Replenishment**: {audit.get('action_required', '')}
- **High-Risk Depletions**:
"""
        for item in inv_data.get("out_of_stock_skus", []):
            response_md += f"  - **{item.get('sku')}** - {item.get('name')} (Est. Loss: {item.get('lost_sales_est', 'N/A')})\n"

    trace.append({
        "step": 6,
        "phase": "RESPONSE_SYNTHESIS",
        "title": "Output Synthesis Complete",
        "detail": f"Generated {len(response_md.splitlines())} lines conforming to '{matched_skill_name}' standard specification."
    })

    return {
        "response": response_md,
        "skill_used": matched_skill_name,
        "trace": trace
    }


# Static Files Mount
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def read_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"status": "ACME Retail Skills & ADK Server Active"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("DEMO_PORT", 8080))
    print(f"🚀 Launching ACME Retail Skills & ADK Agent Dashboard on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
