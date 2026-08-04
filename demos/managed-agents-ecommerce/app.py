import os
import logging
import json
import uuid
import subprocess
import io
import zipfile
import base64
import requests
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import RedirectResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("unified_commerce_managed_agents")

app = FastAPI(title="Unified Commerce Agent Control Room")

PROJECT_ID = os.getenv("GCP_PROJECT", "truiz-agent-builder")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
SKILL_GCS_BUCKET = os.getenv("SKILL_GCS_BUCKET", "truiz-agent-builder-managed-agents")

# Initialize GenAI Client
try:
    from google import genai
    from google.genai import types
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    logger.info(f"Successfully initialized google-genai client (Project: {PROJECT_ID}, Location: {LOCATION})")
except Exception as e:
    logger.error(f"Failed to initialize google-genai client: {e}")
    client = None

# Request Models
class AgentCreateRequest(BaseModel):
    id: str = "unified-commerce-agent"
    base_agent: str = "antigravity-preview-05-2026"
    description: Optional[str] = "Unified Assistant bridging OmniCommerce Marketing, Commerce, and Service Clouds."
    system_instruction: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    base_environment: Optional[Dict[str, Any]] = None

class AgentUpdateRequest(BaseModel):
    description: Optional[str] = None
    system_instruction: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    base_environment: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    agent: str
    input: str
    environment: Optional[Any] = None

class SkillCreateRequest(BaseModel):
    id: str
    display_name: str
    description: str
    skill_md_content: str

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "merchant_data")

# Helper Auth Headers for GCP REST Calls
def get_auth_headers() -> dict:
    try:
        import google.auth
        import google.auth.transport.requests
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        return {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json"
        }
    except Exception as e:
        logger.error(f"Failed to retrieve credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication Failed: {str(e)}")

def get_skills_api_url(skill_id: Optional[str] = None) -> str:
    skill_location = "us-central1"
    host = f"{skill_location}-aiplatform.googleapis.com"
    url = f"https://{host}/v1beta1/projects/{PROJECT_ID}/locations/{skill_location}/skills"
    return url

# --- STARTUP AUTOMATIC AGENT PROVISIONING ---
@app.on_event("startup")
async def startup_event():
    logger.info("Server startup: Syncing unified-commerce-agent configuration on Control Plane...")
    try:
        headers = get_auth_headers()
        del_url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/agents/unified-commerce-agent"
        requests.delete(del_url, headers=headers)

        create_url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/agents"
        system_instruction = (
            "* You are \"Omni-AI\", an advanced retail assistant designed for OmniCommerce merchants to automate multi-channel engagement and service helpdesks.\n"
            "* You support three unified pillars: Commerce Cloud (inventory, specs), Marketing Cloud (segment copy, cart recovery), and Service Cloud (helpdesk tickets).\n"
            "* When checking product inventory or customer profiles, inspect `catalog.json`, `orders.json`, `customers.json`, or `tickets.json` in your workspace (under `./` or `./merchant_data/`).\n"
            "* Always prioritize the customer's eRFM profile (Recency, Frequency, Monetary Value) to recommend upsell products.\n"
            "* If stock is <= 5 units, append a high-converting scarcity alert.\n"
            "* If a customer requests refunds over $150, draft a structured ticket JSON and trigger the \"Escalate to Human Agent\" protocol.\n\n"
            "Rule: You must always explain your reasoning (e.g., why a promotional offer matches a segment) and narrate your actions."
        )
        payload = {
            "id": "unified-commerce-agent",
            "base_agent": "antigravity-preview-05-2026",
            "description": "Unified Assistant bridging OmniCommerce Marketing, Commerce, and Service Clouds.",
            "system_instruction": system_instruction,
            "tools": [{"type": "code_execution"}, {"type": "google_search"}],
            "base_environment": {
                "type": "remote",
                "sources": [
                    {"type": "gcs", "source": f"gs://{SKILL_GCS_BUCKET}/merchant_data", "target": "merchant_data"},
                    {"type": "gcs", "source": f"gs://{SKILL_GCS_BUCKET}/skills", "target": "skills"}
                ],
                "network": {"allowlist": [{"domain": "*"}]}
            }
        }
        create_res = requests.post(create_url, json=payload, headers=headers)
        logger.info(f"Agent unified-commerce-agent synced cleanly (Status: {create_res.status_code})")
    except Exception as e:
        logger.error(f"Startup default agent check error: {e}")

# --- MERCHANT DATABASE ENDPOINTS ---

@app.get("/api/merchant/catalog")
async def get_merchant_catalog():
    catalog_path = os.path.join(DATA_DIR, "catalog.json")
    if os.path.exists(catalog_path):
        with open(catalog_path, "r") as f:
            return json.load(f)
    return []

@app.get("/api/merchant/customers")
async def get_merchant_customers():
    customers_path = os.path.join(DATA_DIR, "customers.json")
    if os.path.exists(customers_path):
        with open(customers_path, "r") as f:
            return json.load(f)
    return []

@app.get("/api/merchant/orders")
async def get_merchant_orders():
    orders_path = os.path.join(DATA_DIR, "orders.json")
    if os.path.exists(orders_path):
        with open(orders_path, "r") as f:
            return json.load(f)
    return []

@app.get("/api/merchant/tickets")
async def get_merchant_tickets():
    tickets_path = os.path.join(DATA_DIR, "tickets.json")
    if os.path.exists(tickets_path):
        with open(tickets_path, "r") as f:
            return json.load(f)
    return []

@app.post("/api/merchant/reset")
async def reset_merchant_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    catalog = [
        {
            "sku": "UB-RUN-100",
            "name": "UltraBoost Performance Running Shoes",
            "category": "Footwear",
            "price": 140.00,
            "stock_quantity": 3,
            "colors": ["Black", "Blue", "White"],
            "sizes": [8, 9, 10, 11]
        },
        {
            "sku": "APX-JKT-200",
            "name": "Apex Thermal Winter Jacket",
            "category": "Apparel",
            "price": 220.00,
            "stock_quantity": 25,
            "colors": ["Navy", "Olive", "Charcoal"],
            "sizes": ["S", "M", "L", "XL"]
        },
        {
            "sku": "NMD-BAG-300",
            "name": "Nomad Leather Weekend Duffel Bag",
            "category": "Accessories",
            "price": 185.00,
            "stock_quantity": 2,
            "colors": ["Tan", "Espresso"],
            "sizes": ["Standard"]
        },
        {
            "sku": "SLR-WTC-400",
            "name": "SolarPulse Smartwatch Pro",
            "category": "Electronics",
            "price": 299.00,
            "stock_quantity": 40,
            "colors": ["Obsidian", "Titanium"],
            "sizes": ["42mm", "46mm"]
        }
    ]

    orders = [
        {
            "order_id": "90210",
            "customer_email": "sarah.jenkins@example.com",
            "order_date": "2026-07-02",
            "status": "Delayed in Transit",
            "carrier": "FedEx",
            "tracking_number": "TRK987654321",
            "expected_delivery": "2026-07-10",
            "items": [{"sku": "UB-RUN-100", "name": "UltraBoost Running Shoes", "size": "10", "price": 140.00, "quantity": 1}],
            "total_amount": 140.00
        },
        {
            "order_id": "90211",
            "customer_email": "alex.chen@example.com",
            "order_date": "2026-07-15",
            "status": "Delivered",
            "carrier": "UPS",
            "tracking_number": "TRK123456789",
            "expected_delivery": "2026-07-18",
            "items": [{"sku": "SLR-WTC-400", "name": "SolarPulse Smartwatch Pro", "size": "46mm", "price": 299.00, "quantity": 1}],
            "total_amount": 299.00
        }
    ]

    customers = [
        {
            "customer_id": "CUST-101",
            "name": "Sarah Jenkins",
            "email": "sarah.jenkins@example.com",
            "erfm_segment": "VIP High-Value",
            "recency_days": 5,
            "frequency_orders": 14,
            "total_monetary_spend": 3450.00,
            "vip_tier": "Gold",
            "abandoned_cart": {
                "sku": "NMD-BAG-300",
                "name": "Nomad Leather Weekend Duffel Bag",
                "price": 185.00
            }
        },
        {
            "customer_id": "CUST-102",
            "name": "Mike Ross",
            "email": "mike.ross@example.com",
            "erfm_segment": "At-Risk Churn",
            "recency_days": 90,
            "frequency_orders": 2,
            "total_monetary_spend": 180.00,
            "vip_tier": "Bronze",
            "abandoned_cart": {
                "sku": "APX-JKT-200",
                "name": "Apex Thermal Winter Jacket",
                "price": 220.00
            }
        }
    ]

    tickets = [
        {
            "ticket_id": "TK-1001",
            "customer_email": "sarah.jenkins@example.com",
            "order_id": "90210",
            "subject": "Order #90210 Delayed in Transit",
            "status": "Open",
            "priority": "High",
            "cloud": "Service Cloud"
        }
    ]

    with open(os.path.join(DATA_DIR, "catalog.json"), "w") as f:
        json.dump(catalog, f, indent=2)
    with open(os.path.join(DATA_DIR, "orders.json"), "w") as f:
        json.dump(orders, f, indent=2)
    with open(os.path.join(DATA_DIR, "customers.json"), "w") as f:
        json.dump(customers, f, indent=2)
    with open(os.path.join(DATA_DIR, "tickets.json"), "w") as f:
        json.dump(tickets, f, indent=2)

    return {"status": "success", "message": "Merchant seed dataset successfully reset."}


# --- ENVIRONMENT WORKSPACE & SKILLS ENDPOINTS ---

@app.get("/api/environment/workspace")
async def get_environment_workspace():
    files = []
    if os.path.exists(DATA_DIR):
        for f in sorted(os.listdir(DATA_DIR)):
            file_path = os.path.join(DATA_DIR, f)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    "name": f,
                    "relative_path": f"merchant_data/{f}",
                    "target_path": f"/workspace/merchant_data/{f}",
                    "size_bytes": stat.st_size
                })
    return {
        "workspace_root": "/workspace",
        "container_cwd": "/workspace",
        "merchant_data_path": "/workspace/merchant_data",
        "files": files
    }

@app.get("/api/environment/workspace/file")
async def read_workspace_file(path: str):
    safe_path = os.path.normpath(path)
    if safe_path.startswith("..") or safe_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid relative path")
    
    full_path = os.path.join(BASE_DIR, safe_path)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {
        "path": safe_path,
        "target_path": f"/workspace/{safe_path}",
        "content": content
    }

@app.get("/api/environment/skills")
async def get_environment_skills():
    skills = []
    skill_file = os.path.join(BASE_DIR, "unified_commerce_skill.md")
    if os.path.exists(skill_file):
        with open(skill_file, "r", encoding="utf-8") as f:
            content = f.read()
        skills.append({
            "id": "unified_commerce_skill",
            "name": "Unified Commerce Master Directive",
            "filename": "unified_commerce_skill.md",
            "target_path": "/workspace/skills/unified_commerce_skill.md",
            "gcs_source": f"gs://{SKILL_GCS_BUCKET}/skills/unified_commerce_skill.md",
            "content": content
        })
    return {
        "skills_root": "/workspace/skills",
        "gcs_bucket": SKILL_GCS_BUCKET,
        "skills": skills
    }

# --- MANAGED AGENTS CONTROL PLANE ENDPOINTS ---

@app.get("/api/project-info")
async def get_project_info():
    return {
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "skill_bucket": SKILL_GCS_BUCKET
    }

@app.get("/api/agents")
async def list_agents():
    try:
        url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/agents"
        headers = get_auth_headers()
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return {"agents": []}
        data = res.json()
        agents_list = []
        if "agents" in data:
            for a in data["agents"]:
                name = a.get("name", "")
                agent_id = a.get("id") or name.split("/")[-1]
                agents_list.append({
                    "id": agent_id,
                    "name": name,
                    "base_agent": a.get("base_agent"),
                    "description": a.get("description"),
                    "system_instruction": a.get("system_instruction"),
                    "tools": a.get("tools", []),
                    "base_environment": a.get("base_environment")
                })
        return {"agents": agents_list}
    except Exception as e:
        logger.error(f"Failed to list agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")

@app.post("/api/agents")
async def create_agent(req: AgentCreateRequest):
    try:
        system_instruction = req.system_instruction or (
            "* You are \"Omni-AI\", an advanced retail assistant designed for OmniCommerce merchants to automate multi-channel engagement and service helpdesks.\n"
            "* You support three unified pillars: Commerce Cloud (inventory, specs), Marketing Cloud (segment copy, cart recovery), and Service Cloud (helpdesk tickets).\n"
            "* When starting up, parse the local repository `./merchant_data/` to load product catalogs, active customer order history, and active tickets.\n"
            "* Always prioritize the customer's eRFM profile (Recency, Frequency, Monetary Value) to recommend upsell products.\n"
            "* If a customer uses highly frustrated language or requests refunds over $150, draft a structured ticket JSON and trigger the \"Escalate to Human Agent\" protocol.\n\n"
            "Rule: You must always explain your reasoning (e.g., why a promotional offer matches a segment) and narrate your actions."
        )

        tools = [
            {"type": "filesystem"},
            {"type": "google_search"}
        ]

        base_env = req.base_environment or {
            "type": "remote",
            "sources": [
                {
                    "type": "gcs",
                    "source": f"gs://{SKILL_GCS_BUCKET}/merchant_data",
                    "target": "merchant_data"
                },
                {
                    "type": "gcs",
                    "source": f"gs://{SKILL_GCS_BUCKET}/skills",
                    "target": "skills"
                }
            ],
            "network": {
                "allowlist": [{"domain": "*"}]
            }
        }

        url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/agents"
        headers = get_auth_headers()
        payload = {
            "id": req.id,
            "base_agent": req.base_agent,
            "description": req.description,
            "system_instruction": system_instruction,
            "tools": tools,
            "base_environment": base_env
        }

        logger.info(f"Creating agent {req.id} via REST...")
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code not in [200, 201]:
            logger.warning(f"Create agent REST response status: {res.status_code}, response: {res.text}")
        
        return {"id": req.id, "base_agent": req.base_agent, "description": req.description, "status": "created"}
    except Exception as e:
        logger.error(f"Failed to create agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")

@app.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: str):
    try:
        url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/agents/{agent_id}"
        headers = get_auth_headers()
        res = requests.delete(url, headers=headers)
        return {"status": "success", "message": f"Agent {agent_id} deletion submitted"}
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")

@app.post("/api/chat")
async def handle_chat(req: ChatRequest):
    url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/interactions"

    # Agent target resource name format
    agent_target = req.agent
    if not agent_target.startswith("projects/"):
        agent_target = f"projects/{PROJECT_ID}/locations/{LOCATION}/agents/{req.agent}"

    payload = {
        "agent": agent_target,
        "input": req.input,
        "stream": True,
        "background": True,
        "store": True
    }

    if req.environment and req.environment != "remote":
        payload["environment"] = req.environment

    def sse_generator():
        import time
        max_retries = 6
        retry_delay = 4
        res = None

        for attempt in range(1, max_retries + 1):
            try:
                headers = get_auth_headers()
                logger.info(f"Initiating REST interaction turn for agent: {agent_target} (Attempt {attempt}/{max_retries})")
                res = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)
                
                if res.status_code == 200:
                    break
                
                err_text = res.text
                if ("setup" in err_text.lower() or "resource" in err_text.lower() or res.status_code == 400) and attempt < max_retries:
                    logger.warning(f"Resource setting up (HTTP {res.status_code}), retrying in {retry_delay}s... ({attempt}/{max_retries})")
                    yield f"data: {json.dumps({'type': 'content', 'text': f'*[Initializing container environment sandbox (Attempt {attempt}/{max_retries})... please wait]*\\n\\n'})}\n\n"
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Interaction error HTTP {res.status_code}: {err_text}")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'HTTP {res.status_code}: {err_text}'})}\n\n"
                    return
            except Exception as e:
                logger.error(f"Stream exception on attempt {attempt}: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    return

        if not res or res.status_code != 200:
            return

        current_step_kind = None
        pending_model_text = ""

        try:
            for line in res.iter_lines():
                if not line:
                    continue
                decoded_line = line.decode('utf-8').strip()
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        event_data = json.loads(data_str)
                        event_type = event_data.get("event_type")

                        if event_type in ["interaction.created", "interaction.start"]:
                            interaction_id = event_data.get("interaction", {}).get("id")
                            if interaction_id:
                                yield f"data: {json.dumps({'type': 'interaction_id', 'id': interaction_id})}\n\n"
                        elif event_type in ["interaction.completed", "interaction.complete"]:
                            env_id = event_data.get("interaction", {}).get("environment_id")
                            if env_id:
                                yield f"data: {json.dumps({'type': 'env_id', 'env_id': env_id})}\n\n"

                        if event_type == "step.start":
                            step_data = event_data.get("step", {})
                            current_step_kind = step_data.get("type", "")
                            # If a tool execution step starts, flush any preceding model output text as thought!
                            if current_step_kind in ["function_call", "function_result"]:
                                if pending_model_text:
                                    yield f"data: {json.dumps({'type': 'thought', 'text': pending_model_text})}\n\n"
                                    pending_model_text = ""

                        if event_type in ["step.delta", "content.delta"]:
                            delta = event_data.get("delta", {})
                            delta_type = delta.get("type")
                            if delta_type == "text" or "text" in delta:
                                text = delta.get("text", "")
                                if text:
                                    if current_step_kind in ["function_call", "function_result"]:
                                        yield f"data: {json.dumps({'type': 'thought', 'text': text})}\n\n"
                                    else:
                                        pending_model_text += text
                                        lower_text = pending_model_text.strip().lower()
                                        if any(lower_text.startswith(p) for p in ["i will", "i am", "i have", "i'll", "my actions", "my reasoning", "exploration:", "summary of"]):
                                            yield f"data: {json.dumps({'type': 'thought', 'text': pending_model_text})}\n\n"
                                            pending_model_text = ""
                            elif delta_type == "arguments_delta" or "arguments" in delta:
                                code = delta.get("arguments", "")
                                if code:
                                    if pending_model_text:
                                        yield f"data: {json.dumps({'type': 'thought', 'text': pending_model_text})}\n\n"
                                        pending_model_text = ""
                                    yield f"data: {json.dumps({'type': 'trace_code', 'code': code})}\n\n"
                    except json.JSONDecodeError:
                        pass

            if pending_model_text:
                yield f"data: {json.dumps({'type': 'content', 'text': pending_model_text})}\n\n"
                pending_model_text = ""
        except Exception as e:
            logger.error(f"Error reading SSE stream: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")

@app.post("/api/diagnostics")
async def run_diagnostics():
    report = {
        "auth": False,
        "project_id": PROJECT_ID,
        "api_enabled": False,
        "skill_bucket": SKILL_GCS_BUCKET
    }
    try:
        sa_token = subprocess.check_output(
            ["gcloud", "auth", "application-default", "print-access-token"], text=True
        ).strip()
        report["auth"] = True if sa_token else False
    except Exception:
        report["auth"] = False

    try:
        res = subprocess.check_output(
            ["gcloud", "services", "list", f"--project={PROJECT_ID}", "--enabled", "--filter=name:aiplatform.googleapis.com", "--format=value(name)"],
            text=True
        ).strip()
        report["api_enabled"] = "aiplatform.googleapis.com" in res
    except Exception:
        report["api_enabled"] = False

    return report

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8005, reload=True)
