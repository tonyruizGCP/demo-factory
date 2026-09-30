"""Offline High-Fidelity Simulation & Demo Factory Harness Adapter.

Provides deterministic simulation outputs for `app/eval_runner.py` and the
Demo Factory Interactive Harness Runner when testing agent trajectories.
"""

from typing import Any


SIMULATION_DATABASE: dict[str, dict[str, Any]] = {
    "default": {
        "agent_response": (
            "Acme Inc. Creative Studio workspace opened in Gemini Enterprise (`ui://acme/creative-studio`). "
            "I have ingested your reference product image and brand brief, launched background job "
            "`job_omni_banana_01` using Gemini Omni (`gemini-omni-flash-preview`) and Nano Banana "
            "(`gemini-3.1-flash-image-preview`), notified the studio upon completion, and saved "
            "immutable content version `v2` to `gs://truiz-agy-demo-acme-creative-studio-assets/campaigns/acme_trailblazer_x1/versions/v2/bundle.json`."
        ),
        "thought_process": [
            "Perceive Goal: Open Acme Inc. Creative Studio MCP App and create multimodal ad copy + visual creative from reference assets",
            "Context Check: Validate AGENTS.md rules (anti-canvas routing, <2s async job initiation, GCS version persistence)",
            "Act: Invoke MCP tool 'upload_reference_asset' to stage reference image & brand brief in GCS",
            "Act: Invoke MCP tool 'create_ad_campaign_job' (Gemini Omni + Nano Banana async pipeline)",
            "Observe: Poll 'get_studio_state' / 'get_job_status' until job transitions queued -> running -> completed (100%)",
            "Verify: Confirm immutable content version v2 is saved in GCS bucket and inspectable via 'get_content_version'"
        ],
        "tool_calls": [
            {
                "tool_name": "open_creative_studio",
                "arguments": {"campaign_id": "acme_trailblazer_x1"},
                "result": {
                    "status": "ok",
                    "resourceUri": "ui://acme/creative-studio",
                    "preferredMode": "pip",
                    "active_version_id": "v1"
                }
            },
            {
                "tool_name": "upload_reference_asset",
                "arguments": {
                    "campaign_id": "acme_trailblazer_x1",
                    "filename": "trailblazer_x1_hero.svg",
                    "asset_type": "image"
                },
                "result": {
                    "status": "uploaded",
                    "gcs_uri": "gs://truiz-agy-demo-acme-creative-studio-assets/campaigns/acme_trailblazer_x1/references/trailblazer_x1_hero.svg"
                }
            },
            {
                "tool_name": "create_ad_campaign_job",
                "arguments": {
                    "campaign_id": "acme_trailblazer_x1",
                    "prompt_instructions": "Create a high-energy marathon launch campaign highlighting 14% energy return and AeroFoam.",
                    "aspect_ratio": "1:1"
                },
                "result": {
                    "job_id": "job_omni_banana_01",
                    "status": "running",
                    "models": ["gemini-omni-flash-preview", "gemini-3.1-flash-image-preview (Nano Banana)"]
                }
            },
            {
                "tool_name": "get_content_version",
                "arguments": {
                    "campaign_id": "acme_trailblazer_x1",
                    "version_id": "v2"
                },
                "result": {
                    "version_id": "v2",
                    "bundle_gcs_uri": "gs://truiz-agy-demo-acme-creative-studio-assets/campaigns/acme_trailblazer_x1/versions/v2/bundle.json",
                    "status": "verified"
                }
            }
        ],
        "eval_scores": {
            "FINAL_RESPONSE_QUALITY": 0.98,
            "TRAJECTORY_COMPLIANCE": 0.99,
            "SAFETY_GUARDRAILS": 1.0,
            "TOKEN_EFFICIENCY": 0.94
        }
    }
}


def get_simulated_response(user_input: str) -> dict[str, Any]:
    res = dict(SIMULATION_DATABASE["default"])
    if user_input:
        res["agent_response"] = (
            f"[Acme Inc. Creative Studio MCP App] Processed request: '{user_input}'. "
            + res["agent_response"]
        )
    return res
