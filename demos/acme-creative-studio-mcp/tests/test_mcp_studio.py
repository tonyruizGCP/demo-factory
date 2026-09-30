"""Comprehensive unit & integration tests for Acme Inc. Creative Studio MCP App."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DISABLE_LIVE_GCS"] = "1"

from app.agent import app as adk_app, root_agent
from app.main import app as fastapi_app
from app.mcp_server import CreativeStudioRuntime, dispatch_mcp_method


def test_adk_agent_exports():
    """Verify ADK root_agent and app exports follow Demo Factory conventions."""
    assert root_agent.name == "acme-creative-studio-agent"
    assert adk_app.name == "acme-creative-studio-agent"
    assert "canvas_agent" in root_agent.instruction


def test_mcp_initialize_and_multi_dialect_ui_meta():
    """Verify Streamable HTTP MCP initialize, tools/list, and resources/read."""
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = CreativeStudioRuntime(mirror_root=Path(tmpdir))

            init_res = await dispatch_mcp_method(runtime, "initialize", {})
            assert init_res["protocolVersion"] == "2025-06-18"
            assert "tools" in init_res["capabilities"]
            assert "resources" in init_res["capabilities"]

            tools_res = await dispatch_mcp_method(runtime, "tools/list", {})
            tools_by_name = {t["name"]: t for t in tools_res["tools"]}
            assert "open_creative_studio" in tools_by_name
            assert "create_ad_campaign_job" in tools_by_name
            assert "upload_reference_asset" in tools_by_name
            assert "compare_content_versions" in tools_by_name

            open_meta = tools_by_name["open_creative_studio"]["_meta"]
            assert open_meta["ui"]["resourceUri"] == "ui://acme/creative-studio"
            assert open_meta["ui"]["preferredMode"] == "pip"
            assert open_meta["io.modelcontextprotocol/ui"]["resourceUri"] == "ui://acme/creative-studio"
            assert tools_by_name["open_creative_studio"]["meta"]["ui"]["resourceUri"] == "ui://acme/creative-studio"

            # Verify resources/read strips Gemini Enterprise #fragment nonces
            read_res = await dispatch_mcp_method(
                runtime,
                "resources/read",
                {"uri": "ui://acme/creative-studio#ge-instance-42"},
            )
            content = read_res["contents"][0]
            assert content["uri"] == "ui://acme/creative-studio"
            assert content["mimeType"] == "text/html;profile=mcp-app"
            assert "Acme Inc. Creative Studio" in content["text"]

    asyncio.run(_run())


def test_upload_reference_and_async_job_and_gcs_versions():
    """Verify reference uploads, async job tracking + notifications, and GCS version diffs/restore."""
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = CreativeStudioRuntime(mirror_root=Path(tmpdir))
            campaign_id = "acme_trailblazer_x1"

            # 1. Initial seeded version v1 exists
            versions_res = await dispatch_mcp_method(
                runtime,
                "tools/call",
                {"name": "list_content_versions", "arguments": {"campaign_id": campaign_id}},
            )
            initial_versions = versions_res["structuredContent"]["versions"]
            assert len(initial_versions) == 1
            assert initial_versions[0]["version_number"] == 1
            assert initial_versions[0]["gcs_uri"].startswith("gs://")

            # 2. Upload a reference image + brand note (testing Dolphin prefix stripping too)
            upload_res = await dispatch_mcp_method(
                runtime,
                "tools/call",
                {
                    "name": "custom_mcp_acme_connector_agent__upload_reference_asset",
                    "arguments": {
                        "campaign_id": campaign_id,
                        "filename": "ridge_hero_ref.svg",
                        "content_type": "image/svg+xml",
                        "data_uri": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64'><circle cx='32' cy='32' r='30' fill='%23FACC15'/></svg>",
                        "notes": "High-contrast yellow sun crest over titanium ridge.",
                    },
                },
            )
            ref_info = upload_res["structuredContent"]["reference"]
            assert ref_info["filename"] == "ridge_hero_ref.svg"
            assert ref_info["asset_type"] == "image"
            assert ref_info["gcs_uri"].startswith("gs://")

            # 3. Launch an async Gemini Omni + Nano Banana generation job
            create_job_res = await dispatch_mcp_method(
                runtime,
                "tools/call",
                {
                    "name": "create_ad_campaign_job",
                    "arguments": {
                        "campaign_id": campaign_id,
                        "creative_prompt": "Include a 25% Launch Week Offer badge and emphasize ultralight carbon sole.",
                        "aspect_ratio": "16:9",
                        "tone_override": "Playful, witty, high-energy",
                    },
                },
            )
            job_data = create_job_res["structuredContent"]["job"]
            job_id = job_data["job_id"]
            assert job_data["status"] in ("queued", "running")

            # Poll until job finishes
            final_job = None
            for _ in range(30):
                await asyncio.sleep(0.12)
                poll_res = await dispatch_mcp_method(
                    runtime,
                    "tools/call",
                    {"name": "get_job_status", "arguments": {"job_id": job_id}},
                )
                j = poll_res["structuredContent"]["job"]
                if j["status"] == "completed":
                    final_job = j
                    break

            assert final_job is not None
            assert final_job["progress_pct"] == 100
            assert final_job["result_version"]["version_number"] == 2

            # 4. Verify unread notifications were created for the user and can be acknowledged
            state_res = await dispatch_mcp_method(
                runtime,
                "tools/call",
                {"name": "get_studio_state", "arguments": {"campaign_id": campaign_id}},
            )
            unread = state_res["structuredContent"]["studio_state"]["unread_notifications"]
            assert len(unread) >= 1
            notif_id = unread[0]["notification_id"]

            ack_res = await dispatch_mcp_method(
                runtime,
                "tools/call",
                {
                    "name": "acknowledge_job_notification",
                    "arguments": {"campaign_id": campaign_id, "notification_id": notif_id},
                },
            )
            remaining_ids = {
                n["notification_id"] for n in ack_res["structuredContent"]["unread_notifications"]
            }
            assert notif_id not in remaining_ids

            # 5. Refine ad copy interactively to create v3
            refine_res = await dispatch_mcp_method(
                runtime,
                "tools/call",
                {
                    "name": "refine_ad_copy_job",
                    "arguments": {
                        "campaign_id": campaign_id,
                        "headline": "Conquer Every Summit in Ultralight Titanium",
                        "cta_text": "Claim 25% Launch Offer",
                        "edit_notes": "Updated headline and CTA for Q4 promo",
                    },
                },
            )
            v3 = refine_res["structuredContent"]["version"]
            assert v3["version_number"] == 3
            assert v3["ad_copy"]["headline"] == "Conquer Every Summit in Ultralight Titanium"

            # 6. Compare v1 and v3
            diff_res = await dispatch_mcp_method(
                runtime,
                "tools/call",
                {
                    "name": "compare_content_versions",
                    "arguments": {"campaign_id": campaign_id, "version_a": 1, "version_b": 3},
                },
            )
            comp = diff_res["structuredContent"]["comparison"]
            assert comp["total_fields_changed"] >= 1
            assert "Conquer Every Summit" in comp["unified_diff"]

            # 7. Restore v1 -> creates v4
            restore_res = await dispatch_mcp_method(
                runtime,
                "tools/call",
                {
                    "name": "restore_content_version",
                    "arguments": {"campaign_id": campaign_id, "version_number": 1},
                },
            )
            v4 = restore_res["structuredContent"]["restored_version"]
            assert v4["version_number"] == 4
            assert v4["restored_from_version"] == 1

    asyncio.run(_run())


def test_fastapi_http_routes_and_downloads():
    """Verify FastAPI HTTP endpoints (/health, /app, /mcp, /download/{token}, /api/query)."""
    client = TestClient(fastapi_app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["customer"] == "Acme Inc."

    ui_page = client.get("/app")
    assert ui_page.status_code == 200
    assert "Acme Inc. Creative Studio" in ui_page.text

    mcp_post = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/call",
            "params": {
                "name": "open_creative_studio",
                "arguments": {"campaign_id": "acme_pulse_espresso"},
            },
        },
    )
    assert mcp_post.status_code == 200
    payload = mcp_post.json()
    sc = payload["result"]["structuredContent"]
    assert sc["studio_state"]["campaign_id"] == "acme_pulse_espresso"

    # Test signed download link for creative.svg
    svg_url = sc["studio_state"]["active_version"]["download_urls"]["creative_svg"]
    dl_resp = client.get(svg_url)
    assert dl_resp.status_code == 200
    assert "<svg" in dl_resp.text

    # Test DELETE /mcp returns 204 and GET /mcp returns 405
    assert client.delete("/mcp").status_code == 204
    assert client.get("/mcp").status_code == 405

    # Test Demo Factory /api/query endpoint
    q_resp = client.post(
        "/api/query",
        json={"prompt": "Open the Acme Creative Studio and compare versions"},
    )
    assert q_resp.status_code == 200
    assert q_resp.json()["customer"] == "Acme Inc."
