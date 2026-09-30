"""Evaluation runner for Acme Inc. Creative Studio MCP App (`>= 0.85` quality gate)."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

os.environ.setdefault("DISABLE_LIVE_GCS", "1")

from app.mcp_server import CreativeStudioRuntime, dispatch_mcp_method


async def run_evaluation_suite() -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime = CreativeStudioRuntime(mirror_root=Path(tmpdir))
        results: List[Dict[str, Any]] = []

        # Case 1: MCP Initialize + Tools List + UI Resource Discovery
        init_res = await dispatch_mcp_method(runtime, "initialize", {})
        tools_res = await dispatch_mcp_method(runtime, "tools/list", {})
        res_read = await dispatch_mcp_method(
            runtime,
            "resources/read",
            {"uri": "ui://acme/creative-studio#ge-nonce-123"},
        )
        tool_names = {t["name"] for t in tools_res.get("tools", [])}
        case1_pass = (
            init_res.get("protocolVersion") == "2025-06-18"
            and "open_creative_studio" in tool_names
            and "create_ad_campaign_job" in tool_names
            and "upload_reference_asset" in tool_names
            and "compare_content_versions" in tool_names
            and res_read["contents"][0]["mimeType"] == "text/html;profile=mcp-app"
        )
        results.append(
            {
                "case": "mcp_protocol_and_ui_resource_handshake",
                "score": 1.0 if case1_pass else 0.0,
                "passed": case1_pass,
            }
        )

        # Case 2: Reference Image & Brand Content Upload to GCS
        upload_res = await dispatch_mcp_method(
            runtime,
            "tools/call",
            {
                "name": "custom_mcp_acme_agent__upload_reference_asset",
                "arguments": {
                    "campaign_id": "acme_trailblazer_x1",
                    "filename": "alpine_summit_reference.svg",
                    "content_type": "image/svg+xml",
                    "data_uri": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'><rect width='100' height='100' fill='%2338BDF8'/></svg>",
                    "notes": "Hero ridge silhouette reference with cyan accent.",
                },
            },
        )
        sc2 = upload_res.get("structuredContent", {})
        case2_pass = (
            sc2.get("status") == "uploaded"
            and sc2.get("reference", {}).get("gcs_uri", "").startswith("gs://")
        )
        results.append(
            {
                "case": "reference_image_and_content_upload_to_gcs",
                "score": 1.0 if case2_pass else 0.0,
                "passed": case2_pass,
            }
        )

        # Case 3: Async Gemini Omni + Nano Banana Job Creation, State Tracking & Notification
        job_res = await dispatch_mcp_method(
            runtime,
            "tools/call",
            {
                "name": "create_ad_campaign_job",
                "arguments": {
                    "campaign_id": "acme_trailblazer_x1",
                    "creative_prompt": "Add a 20% Summer Summit Launch promo badge and bold urgency CTA.",
                    "aspect_ratio": "16:9",
                    "tone_override": "Bold, cinematic, high-converting",
                },
            },
        )
        sc3 = job_res.get("structuredContent", {})
        job_id = sc3.get("job", {}).get("job_id")
        # Wait for background job completion
        completed_job = None
        for _ in range(30):
            await asyncio.sleep(0.15)
            status_call = await dispatch_mcp_method(
                runtime,
                "tools/call",
                {"name": "get_job_status", "arguments": {"job_id": job_id}},
            )
            job_info = status_call.get("structuredContent", {}).get("job", {})
            if job_info.get("status") == "completed":
                completed_job = job_info
                break

        case3_pass = (
            completed_job is not None
            and completed_job.get("progress_pct") == 100
            and completed_job.get("result_version", {}).get("version_number") == 2
        )
        results.append(
            {
                "case": "async_job_lifecycle_and_user_notifications",
                "score": 1.0 if case3_pass else 0.0,
                "passed": case3_pass,
            }
        )

        # Case 4: GCS Content Versioning, Diff Comparison & Version Restoration
        diff_call = await dispatch_mcp_method(
            runtime,
            "tools/call",
            {
                "name": "compare_content_versions",
                "arguments": {
                    "campaign_id": "acme_trailblazer_x1",
                    "version_a": 1,
                    "version_b": 2,
                },
            },
        )
        restore_call = await dispatch_mcp_method(
            runtime,
            "tools/call",
            {
                "name": "restore_content_version",
                "arguments": {
                    "campaign_id": "acme_trailblazer_x1",
                    "version_number": 1,
                },
            },
        )
        comp = diff_call.get("structuredContent", {}).get("comparison", {})
        restored = restore_call.get("structuredContent", {}).get("restored_version", {})
        case4_pass = (
            comp.get("total_fields_changed", 0) >= 1
            and restored.get("version_number") == 3
            and restored.get("restored_from_version") == 1
        )
        results.append(
            {
                "case": "gcs_content_versioning_diff_and_restore",
                "score": 1.0 if case4_pass else 0.0,
                "passed": case4_pass,
            }
        )

        avg_score = sum(r["score"] for r in results) / len(results)
        summary = {
            "customer": "Acme Inc.",
            "project": "acme-creative-studio-mcp",
            "average_score": round(avg_score, 3),
            "threshold": 0.85,
            "passed": avg_score >= 0.85,
            "cases": results,
        }
        return summary


def main() -> None:
    report = asyncio.run(run_evaluation_suite())
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
