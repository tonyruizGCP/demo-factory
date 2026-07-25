import time
from typing import Dict, Any

SIMULATION_DATABASE = {
    "default": {
        "agent_response": "Hello! I am your AI Assistant for Test Healthcare Triage Assistant. I can process queries, inspect data, and execute automated actions.",
        "thought_process": [
            "Perceive Goal: Understand user request for Test Healthcare Triage Assistant",
            "Plan Steps: Check guardrails -> Query domain tools -> Verify trajectory",
            "Act: Invoke domain toolset",
            "Observe: Verify output quality score"
        ],
        "tool_calls": [
            {
                "tool_name": "domain_search",
                "arguments": {"query": "initial_context"},
                "result": {"status": "success", "records_found": 3}
            }
        ],
        "eval_scores": {
            "FINAL_RESPONSE_QUALITY": 0.95,
            "TRAJECTORY_COMPLIANCE": 0.98,
            "SAFETY_GUARDRAILS": 1.0
        }
    }
}

def get_simulated_response(user_input: str) -> Dict[str, Any]:
    res = SIMULATION_DATABASE["default"].copy()
    res["agent_response"] = f"Processed request for 'Test Healthcare Triage Assistant': " + user_input + " [Verified via Harness Quality Gate]"
    return res
