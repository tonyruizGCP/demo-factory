import os
import json
import time
import requests
import google.auth
import google.auth.transport.requests

PROJECT_ID = os.getenv("GCP_PROJECT", "truiz-agent-builder")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
SKILL_GCS_BUCKET = os.getenv("SKILL_GCS_BUCKET", "truiz-agent-builder-managed-agents")

def get_auth_headers():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json"
    }

def test_agent_lifecycle():
    headers = get_auth_headers()
    agent_id = "unified-commerce-agent"
    
    # 1. Delete old agent to force container refresh
    print(f"--- 1. Cleaning up existing agent: {agent_id} ---")
    del_url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/agents/{agent_id}"
    del_res = requests.delete(del_url, headers=headers)
    print(f"Delete Status: {del_res.status_code}")
    time.sleep(2)

    # 2. Re-create agent with code_execution and GCS sources
    print(f"\n--- 2. Registering Agent: {agent_id} ---")
    payload = {
        "id": agent_id,
        "base_agent": "antigravity-preview-05-2026",
        "description": "Unified Assistant bridging OmniCommerce Marketing, Commerce, and Service Clouds.",
        "system_instruction": (
            "You are Omni-AI, an advanced retail assistant for OmniCommerce merchants.\n"
            "You have access to merchant datasets in `./merchant_data/catalog.json`, `./merchant_data/orders.json`, and `./merchant_data/customers.json`.\n"
            "When checking product inventory or customer profiles, ALWAYS use Python `code_execution` to open and parse the JSON files under `./merchant_data/`.\n"
            "Example Python code execution:\n"
            "```python\n"
            "import json\n"
            "with open('./merchant_data/catalog.json') as f:\n"
            "    catalog = json.load(f)\n"
            "# process inventory...\n"
            "```\n"
            "If stock is <= 5 units, include a low stock scarcity alert in your final response."
        ),
        "tools": [
            {"type": "code_execution"},
            {"type": "google_search"}
        ],
        "base_environment": {
            "type": "remote",
            "sources": [
                {"type": "gcs", "source": f"gs://{SKILL_GCS_BUCKET}", "target": "."}
            ],
            "network": {"allowlist": [{"domain": "*"}]}
        }
    }
    
    create_url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/agents"
    create_res = requests.post(create_url, json=payload, headers=headers)
    print(f"Create Agent Status: {create_res.status_code}")
    if create_res.status_code not in [200, 201]:
        print("Create Agent Output:", create_res.text)
        return
    
    print("Waiting 6 seconds for container warming...")
    time.sleep(6)

    # 3. Test Interaction Turn (Act 3 Scenario)
    print("\n--- 3. Submitting Interaction Turn (Act 3 Scarcity Check) ---")
    prompt = "Check inventory for 'UltraBoost Performance Running Shoes' in size 10 and warn me if stock is low!"
    interaction_url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/interactions"
    
    interaction_payload = {
        "agent": f"projects/{PROJECT_ID}/locations/{LOCATION}/agents/{agent_id}",
        "input": prompt,
        "stream": True,
        "background": True,
        "store": True
    }
    
    max_attempts = 6
    for attempt in range(1, max_attempts + 1):
        headers = get_auth_headers()
        print(f"Initiating interaction turn (Attempt {attempt}/{max_attempts})...")
        res = requests.post(interaction_url, headers=headers, json=interaction_payload, stream=True, timeout=120)
        
        if res.status_code == 200:
            print("Successfully connected to interaction stream! Processing events...\n")
            for line in res.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8").strip()
                if decoded.startswith("data: "):
                    data_str = decoded[6:]
                    if data_str == "[DONE]":
                        print("\n[STREAM COMPLETE]")
                        break
                    try:
                        event = json.loads(data_str)
                        event_type = event.get("event_type")
                        if event_type == "step.delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text":
                                print(delta.get("text", ""), end="", flush=True)
                            elif delta.get("type") == "arguments_delta":
                                print(f"\n[Code Execution Call]: {delta.get('arguments', '')}", flush=True)
                        elif event_type == "interaction.completed":
                            env_id = event.get("interaction", {}).get("environment_id")
                            print(f"\n\n[Interaction Completed - Environment ID: {env_id}]")
                    except Exception:
                        pass
            break
        else:
            print(f"Attempt {attempt} returned HTTP {res.status_code}: {res.text}")
            if "setup" in res.text.lower() or "resource" in res.text.lower() or res.status_code == 400:
                print("Waiting 5s for container sandbox provisioning...")
                time.sleep(5)
            else:
                break

if __name__ == "__main__":
    test_agent_lifecycle()
