"""MCP App Streamable HTTP Server (`/mcp`) for Acme Inc. Creative Studio.

Implements all architectural patterns and findings from the Cooley Law Motion to Seal
MCP App (`ge-mcp-app-demo`):
1. Hand-rolled JSON-RPC 2.0 over Streamable HTTP (`POST /mcp`, `DELETE /mcp`).
2. Multi-dialect UI metadata (`_meta.ui`, `io.modelcontextprotocol/ui`, `ui/resourceUri`)
   pointing to `ui://acme/creative-studio` (`text/html;profile=mcp-app`).
3. Sandboxed iframe CSP declarations (`RESOURCE_META`) for `gstatic.com` host mounting.
4. Dolphin / AgentFlow custom agent prefix stripping (`custom_mcp_<id>_agent__<tool>`).
5. Non-blocking `< 2s` async background job execution (`create_ad_campaign_job`,
   `refine_ad_copy_job`) with multi-stage progress polling (`get_studio_state`,
   `list_active_jobs`, `get_job_status`) and real-time user notifications.
6. Immutable GCS bucket content versioning (`v1`, `v2`, `v3`, ...) with inspection,
   side-by-side diffing (`compare_content_versions`), and restoration (`restore_content_version`).
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from pathlib import Path
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.creative_engine import (
    ACME_SAMPLE_CAMPAIGNS,
    AcmeCreativeEngine,
    build_nano_banana_creative_svg,
    build_reference_product_svg,
)
from app.gcs_version_store import GcsVersionStore
from app.job_manager import CreativeJobManager

MCP_PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")

UI_META_KEY = "io.modelcontextprotocol/ui"
WIDGET_URI = "ui://acme/creative-studio"
WIDGET_MIME = "text/html;profile=mcp-app"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

RESOURCE_META: dict[str, Any] = {
    "ui": {
        "csp": {
            "resourceDomains": [
                "blob:",
                "data:",
                "https://cdn.jsdelivr.net",
                "https://www.gstatic.com",
                "https://fonts.googleapis.com",
                "https://fonts.gstatic.com",
                "https://*.gstatic.com",
                "https://*.run.app",
                "https://*.googleapis.com",
            ],
            "connectDomains": [
                "blob:",
                "data:",
                "https://*.run.app",
                "https://*.googleapis.com",
            ],
            "frameDomains": [
                "blob:",
                "data:",
                "https://*.run.app",
                "https://*.googleapis.com",
            ],
        },
        "prefersBorder": True,
        "displayMode": "pip",
        "preferredDisplayMode": "pip",
    },
    UI_META_KEY: {
        "csp": {
            "resourceDomains": [
                "blob:",
                "data:",
                "https://cdn.jsdelivr.net",
                "https://www.gstatic.com",
                "https://fonts.googleapis.com",
                "https://fonts.gstatic.com",
                "https://*.gstatic.com",
                "https://*.run.app",
                "https://*.googleapis.com",
            ],
            "connectDomains": [
                "blob:",
                "data:",
                "https://*.run.app",
                "https://*.googleapis.com",
            ],
            "frameDomains": [
                "blob:",
                "data:",
                "https://*.run.app",
                "https://*.googleapis.com",
            ],
        },
        "prefersBorder": True,
        "displayMode": "pip",
        "preferredDisplayMode": "pip",
    },
}


def _build_ui_meta(
    visibility: list[str] | None = None,
    is_widget: bool = False,
    preferred_mode: str = "pip",
) -> dict[str, Any]:
    """Constructs multi-dialect UI metadata for GE & ADK McpTool compatibility."""
    ui_meta: dict[str, Any] = {}
    if visibility:
        ui_meta["visibility"] = list(visibility)
    if is_widget:
        ui_meta["resourceUri"] = WIDGET_URI
        ui_meta["preferredMode"] = preferred_mode
        ui_meta["icon"] = "palette"
        ui_meta["iconUrl"] = (
            "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/palette/default/24px.svg"
        )

    meta: dict[str, Any] = {
        "ui": dict(ui_meta),
        UI_META_KEY: dict(ui_meta),
    }
    if is_widget:
        meta["ui/resourceUri"] = WIDGET_URI
    return meta


class McpToolError(Exception):
    """Domain-level error returned to the model with isError=True."""


class _RpcError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class CreativeStudioRuntime:
    """Singleton state coordinator holding the GCS version store, job manager, and engine."""

    def __init__(
        self,
        store: GcsVersionStore | None = None,
        jobs: CreativeJobManager | None = None,
        engine: AcmeCreativeEngine | None = None,
        mirror_root: str | Path | None = None,
    ) -> None:
        self.store = store or GcsVersionStore(local_mirror_dir=mirror_root)
        self.gcs_store = self.store
        self.jobs = jobs or CreativeJobManager()
        self.job_manager = self.jobs
        self.engine = engine or AcmeCreativeEngine()
        self.active_campaign_id = "acme_trailblazer_x1"
        self.selected_version_by_campaign: dict[str, str] = {}
        self._seeded = False
        self._seed_lock = asyncio.Lock()

    async def ensure_seeded(self) -> None:
        if self._seeded:
            return
        async with self._seed_lock:
            if self._seeded:
                return
            for key in ACME_SAMPLE_CAMPAIGNS:
                await self.engine.seed_sample_campaign(self.store, key)
            self._seeded = True

    def _normalize_version_for_ui(self, ver: dict[str, Any] | None) -> dict[str, Any] | None:
        if not ver:
            return None
        v = dict(ver)
        gcs_info = v.get("gcs") or {}
        v.setdefault("gcs_uri", gcs_info.get("bundle_gcs_uri", ""))
        v.setdefault("summary", v.get("diff_summary") or v.get("author_action") or "")
        v.setdefault("storage_backend", "gcs" if gcs_info.get("live_gcs_synced") else "gcs-mirror")
        v.setdefault(
            "download_urls",
            {
                "ad_copy_md": gcs_info.get("ad_copy_download_url", ""),
                "creative_svg": gcs_info.get("creative_image_download_url", ""),
                "bundle_json": gcs_info.get("bundle_download_url", ""),
            },
        )
        ad_copy = dict(v.get("ad_copy") or {})
        ad_copy.setdefault("primary_text", ad_copy.get("primary_copy", ""))
        ad_copy.setdefault("channel_variations", ad_copy.get("channel_variants") or {})
        ad_copy.setdefault("omni_insights", ad_copy.get("multimodal_grounding_notes") or [])
        v["ad_copy"] = ad_copy

        vis = dict(v.get("visual_creative") or {})
        vis.setdefault("svg_data_uri", vis.get("image_data_uri", ""))
        vis.setdefault("palette", vis.get("color_palette") or [])
        vis.setdefault("model", vis.get("model_used", self.engine.nano_banana_model))
        v["visual_creative"] = vis
        v["visual_asset"] = vis
        return v

    def build_studio_snapshot(
        self,
        campaign_id: str | None = None,
        version_id: str | None = None,
    ) -> dict[str, Any]:
        cid = campaign_id or self.active_campaign_id or "acme_trailblazer_x1"
        self.active_campaign_id = cid
        camp = self.store.get_campaign_sync(cid)
        if not camp:
            camp = self.store.ensure_campaign(cid)

        target_vid = (
            version_id
            or self.selected_version_by_campaign.get(cid)
            or camp.get("active_version_id")
        )
        raw_current_version = self.store.get_version_sync(cid, target_vid)
        current_version = self._normalize_version_for_ui(raw_current_version)
        raw_versions_list = self.store.list_versions_sync(cid)
        versions_list = []
        for rv in raw_versions_list:
            item = dict(rv)
            gcs_info = item.get("gcs") or {}
            item.setdefault("gcs_uri", gcs_info.get("bundle_gcs_uri", ""))
            item.setdefault("summary", item.get("diff_summary") or item.get("author_action") or "")
            item.setdefault(
                "download_urls",
                {
                    "ad_copy_md": gcs_info.get("ad_copy_download_url", ""),
                    "creative_svg": gcs_info.get("creative_image_download_url", ""),
                    "bundle_json": gcs_info.get("bundle_download_url", ""),
                },
            )
            versions_list.append(item)

        jobs_list = []
        for j in self.jobs.list_jobs(campaign_id=cid, limit=15):
            jc = dict(j)
            jc.setdefault("stage_message", jc.get("current_stage", ""))
            jc.setdefault("model_omni", self.engine.omni_model)
            jc.setdefault("model_banana", self.engine.nano_banana_model)
            if jc.get("result_version_id") and not jc.get("result_version"):
                rv_obj = self.store.get_version_sync(cid, jc["result_version_id"])
                if rv_obj:
                    jc["result_version"] = {
                        "version_id": rv_obj["version_id"],
                        "version_number": rv_obj["version_number"],
                        "gcs_uri": rv_obj["gcs"]["bundle_gcs_uri"],
                    }
            jobs_list.append(jc)

        active_jobs = [j for j in jobs_list if j["status"] in ("queued", "running")]
        unread_notifications = self.jobs.list_notifications(
            campaign_id=cid, unread_only=True, limit=10
        )
        all_notifications = self.jobs.list_notifications(
            campaign_id=cid, unread_only=False, limit=15
        )

        refs = []
        for r in camp.get("reference_assets", []):
            rc = dict(r)
            rc.setdefault("data_uri", rc.get("data_uri_preview", ""))
            rc.setdefault("extracted_notes", rc.get("description") or rc.get("extracted_text") or "")
            refs.append(rc)

        campaigns_list = []
        for c in self.store.list_campaigns_sync():
            cc = dict(c)
            cc.setdefault("title", cc.get("name", cc["campaign_id"]))
            campaigns_list.append(cc)

        return {
            "customer": "Acme Inc.",
            "studio_status": "running" if active_jobs else "ready",
            "campaign_id": cid,
            "active_campaign_id": cid,
            "campaign": {
                "campaign_id": camp["campaign_id"],
                "name": camp["name"],
                "title": camp["name"],
                "product_name": camp["product_name"],
                "brand_brief": camp["brand_brief"],
                "brand_guidelines": camp["brand_brief"],
                "target_audience": camp["target_audience"],
                "active_version_id": camp["active_version_id"],
                "viewed_version_id": current_version["version_id"] if current_version else None,
                "total_versions": len(versions_list),
            },
            "campaigns": campaigns_list,
            "available_campaigns": campaigns_list,
            "current_version": current_version,
            "active_version": current_version,
            "versions": versions_list,
            "reference_assets": refs,
            "references": refs,
            "active_jobs": active_jobs,
            "recent_jobs": jobs_list,
            "jobs": jobs_list,
            "unread_notifications": unread_notifications,
            "notifications": all_notifications,
            "gcs_bucket": self.store.bucket_name,
            "models": {
                "gemini_omni": self.engine.omni_model,
                "nano_banana": self.engine.nano_banana_model,
            },
        }

    def build_studio_state(
        self,
        campaign_id: str | None = None,
        version_number: int | str | None = None,
    ) -> dict[str, Any]:
        vid = f"v{version_number}" if isinstance(version_number, int) else version_number
        return self.build_studio_snapshot(campaign_id=campaign_id, version_id=vid)

    def render_widget_html(self, campaign_id: str | None = None) -> str:
        if campaign_id:
            self.active_campaign_id = campaign_id
        return _load_widget_html(self)


TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "acme_creative_studio.html"
)


def _load_widget_html(runtime: CreativeStudioRuntime | None = None) -> str:
    html_text = TEMPLATE_PATH.read_text(encoding="utf-8")
    if runtime is not None:
        try:
            snapshot = runtime.build_studio_snapshot()
            safe_json = json.dumps(snapshot).replace("</", "<\\/")
            html_text = html_text.replace(
                "/*__INITIAL_STUDIO_STATE__*/{}",
                safe_json,
            )
        except Exception:
            pass
    return html_text


# ---------------------------------------------------------------------------
# Tool Handlers
# ---------------------------------------------------------------------------


async def _handle_open_creative_studio(
    runtime: CreativeStudioRuntime, _session_key: str, args: dict[str, Any]
) -> dict[str, Any]:
    await runtime.ensure_seeded()
    campaign_id = str(args.get("campaign_id") or runtime.active_campaign_id or "acme_trailblazer_x1").strip()
    if campaign_id not in ACME_SAMPLE_CAMPAIGNS and not runtime.store.get_campaign_sync(campaign_id):
        runtime.store.ensure_campaign(
            campaign_id=campaign_id,
            name=str(args.get("campaign_name") or f"Acme Inc. — {campaign_id}"),
            product_name=str(args.get("product_name") or "Acme Flagship Product"),
            brand_brief=str(args.get("brand_brief") or ""),
        )
    runtime.active_campaign_id = campaign_id
    version_id = args.get("version_id") or (f"v{args['version_number']}" if args.get("version_number") else None)
    if version_id:
        runtime.selected_version_by_campaign[campaign_id] = str(version_id)

    snapshot = runtime.build_studio_snapshot(campaign_id=campaign_id, version_id=version_id)
    cur_ver = snapshot.get("current_version") or {}
    vid = cur_ver.get("version_id", "v1")
    headline = (cur_ver.get("ad_copy") or {}).get("headline", "Ready for creative generation")
    gcs_uri = (cur_ver.get("gcs") or {}).get("bundle_gcs_uri", f"gs://{runtime.store.bucket_name}/")

    return {
        "_meta": _build_ui_meta(visibility=["model", "app"], is_widget=True, preferred_mode="pip"),
        "structuredContent": {
            **snapshot,
            "studio_state": snapshot,
        },
        "content": [
            {
                "type": "text",
                "text": (
                    f"Acme Inc. Creative Studio workspace is open (`{WIDGET_URI}`).\n"
                    f"- **Active Campaign**: {snapshot['campaign']['name']} (`{campaign_id}`)\n"
                    f"- **Current Version**: `{vid}` — *\"{headline}\"*\n"
                    f"- **GCS Bucket Version URI**: `{gcs_uri}`\n"
                    f"- **Models Active**: Gemini Omni (`{runtime.engine.omni_model}`) + "
                    f"Nano Banana (`{runtime.engine.nano_banana_model}`)\n"
                    f"- **Reference Assets Loaded**: {len(snapshot['reference_assets'])}"
                ),
            }
        ],
    }


async def _handle_create_ad_campaign_job(
    runtime: CreativeStudioRuntime, _session_key: str, args: dict[str, Any]
) -> dict[str, Any]:
    """Starts an async background job (<2s return) using Gemini Omni + Nano Banana."""
    await runtime.ensure_seeded()
    campaign_id = str(args.get("campaign_id") or runtime.active_campaign_id or "acme_trailblazer_x1").strip()
    runtime.active_campaign_id = campaign_id

    if args.get("product_name") or args.get("brand_brief") or args.get("campaign_name"):
        runtime.store.ensure_campaign(
            campaign_id=campaign_id,
            name=args.get("campaign_name"),
            product_name=args.get("product_name"),
            brand_brief=args.get("brand_brief"),
            target_audience=args.get("target_audience"),
        )

    prompt_instructions = str(
        args.get("prompt_instructions")
        or args.get("creative_prompt")
        or args.get("creative_direction")
        or "Generate high-converting multimodal ad copy and Nano Banana hero visual grounded in reference assets."
    ).strip()
    aspect_ratio = str(args.get("aspect_ratio") or "1:1").strip()
    tone = str(args.get("tone") or args.get("tone_override") or "Bold & High-Converting").strip()
    wait_for_completion = bool(args.get("wait_for_completion", False))

    camp = runtime.store.ensure_campaign(campaign_id)
    job_info = runtime.jobs.create_job(
        campaign_id=campaign_id,
        job_type="full_campaign",
        title=f"Gemini Omni + Nano Banana: {camp['product_name']}",
        prompt_summary=prompt_instructions,
        models=[runtime.engine.omni_model, f"{runtime.engine.nano_banana_model} (Nano Banana)"],
    )
    job_id = job_info["job_id"]

    async def _worker() -> None:
        async def _progress(stage: str, pct: float) -> None:
            runtime.jobs.update_job_progress(job_id, stage, pct)

        try:
            version_rec = await runtime.engine.run_generation_pipeline(
                store=runtime.store,
                campaign_id=campaign_id,
                prompt_instructions=prompt_instructions,
                aspect_ratio=aspect_ratio,
                tone=tone,
                progress_cb=_progress,
                job_id=job_id,
                author_action=f"Gemini Omni + Nano Banana Job ({job_id})",
            )
            runtime.selected_version_by_campaign[campaign_id] = version_rec["version_id"]
            runtime.jobs.complete_job(job_id, version_rec)
        except Exception as exc:
            runtime.jobs.fail_job(job_id, f"{type(exc).__name__}: {exc}")

    runtime.jobs.spawn_background_job(job_id, _worker)

    if wait_for_completion:
        await runtime.jobs.wait_for_job(job_id)

    snapshot = runtime.build_studio_snapshot(campaign_id=campaign_id)
    latest_job = runtime.jobs.get_job(job_id) or job_info

    return {
        "_meta": _build_ui_meta(visibility=["model", "app"], is_widget=True, preferred_mode="pip"),
        "structuredContent": {
            "job": latest_job,
            "studio": snapshot,
            "studio_state": snapshot,
        },
        "content": [
            {
                "type": "text",
                "text": (
                    f"🚀 Launched background Creative Studio job `{job_id}` for **{camp['name']}**.\n"
                    f"- **Status**: `{latest_job['status']}` ({latest_job['progress_pct']}%)\n"
                    f"- **Models**: `{runtime.engine.omni_model}` + `{runtime.engine.nano_banana_model}` (Nano Banana)\n"
                    f"- **Directive**: {prompt_instructions}\n"
                    f"- **Target GCS Bucket**: `gs://{runtime.store.bucket_name}/campaigns/{campaign_id}/versions/`\n"
                    "The Creative Studio widget is tracking live job stages and will notify the user on completion."
                ),
            }
        ],
    }


async def _handle_refine_ad_copy_job(
    runtime: CreativeStudioRuntime, _session_key: str, args: dict[str, Any]
) -> dict[str, Any]:
    """Refines ad copy or saves direct interactive edits as a new version in GCS."""
    await runtime.ensure_seeded()
    campaign_id = str(args.get("campaign_id") or runtime.active_campaign_id or "acme_trailblazer_x1").strip()
    runtime.active_campaign_id = campaign_id
    camp = runtime.store.ensure_campaign(campaign_id)

    # Check if direct manual edits were submitted from the interactive studio editor
    direct_headline = args.get("headline")
    direct_primary_copy = args.get("primary_copy") or args.get("primary_text")
    direct_cta = args.get("cta_text")
    direct_subheadline = args.get("subheadline")
    aspect_ratio = str(args.get("aspect_ratio") or "1:1").strip()
    revision_note = args.get("revision_note") or args.get("edit_notes")

    if direct_headline or direct_primary_copy or direct_cta or direct_subheadline is not None:
        base_ver = runtime.store.get_version_sync(campaign_id, args.get("base_version_id"))
        base_copy = dict((base_ver or {}).get("ad_copy") or {})
        base_vis = dict((base_ver or {}).get("visual_creative") or {})

        if direct_headline:
            base_copy["headline"] = str(direct_headline)
        if direct_subheadline is not None:
            base_copy["subheadline"] = str(direct_subheadline)
        if direct_primary_copy:
            base_copy["primary_copy"] = str(direct_primary_copy)
            base_copy["primary_text"] = str(direct_primary_copy)
        if direct_cta:
            base_copy["cta_text"] = str(direct_cta)
        if isinstance(args.get("channel_variants"), dict):
            base_copy["channel_variants"] = {
                **(base_copy.get("channel_variants") or {}),
                **args["channel_variants"],
            }

        job_info = runtime.jobs.create_job(
            campaign_id=campaign_id,
            job_type="refine_copy",
            title=f"Studio Copy & Visual Edit: {camp['product_name']}",
            prompt_summary=str(revision_note or "Interactive studio copy refinement & Nano Banana re-render"),
        )
        job_id = job_info["job_id"]
        runtime.jobs.update_job_progress(
            job_id, "Re-rendering Nano Banana visual overlay & saving version to GCS…", 65.0
        )

        next_v_num = len(camp.get("versions", [])) + 1
        version_label = f"v{next_v_num}"
        ref_images = [a for a in camp.get("reference_assets", []) if a.get("asset_type") == "image"]
        ref_uri = ref_images[-1].get("data_uri_preview", "") if ref_images else ""

        palette = args.get("color_palette") or base_vis.get("color_palette") or ["#0b57d0", "#7c4dff", "#f06292", "#0f172a"]
        if args.get("visual_prompt"):
            base_vis["visual_prompt"] = str(args["visual_prompt"])
        base_vis["aspect_ratio"] = aspect_ratio
        base_vis["color_palette"] = palette

        svg_markup = build_nano_banana_creative_svg(
            headline=base_copy.get("headline", "Acme Inc."),
            subheadline=base_copy.get("subheadline", ""),
            cta_text=base_copy.get("cta_text", "Learn More"),
            product_name=camp["product_name"],
            aspect_ratio=aspect_ratio,
            color_palette=palette,
            reference_image_uri=ref_uri,
            version_label=version_label,
            visual_style_tag="Nano Banana Studio",
        )
        base_vis["svg_markup"] = svg_markup
        base_vis["image_data_uri"] = (
            "data:image/svg+xml;base64,"
            + base64.b64encode(svg_markup.encode("utf-8")).decode("ascii")
        )

        raw_new_ver = await runtime.store.create_content_version(
            campaign_id=campaign_id,
            ad_copy_data=base_copy,
            visual_data=base_vis,
            job_id=job_id,
            author_action=str(args.get("author_action") or "Interactive Copy & Visual Refinement"),
            prompt_used=str(revision_note or "Direct copy edit in Creative Studio"),
            parent_version_id=base_ver["version_id"] if base_ver else None,
        )
        new_ver = runtime._normalize_version_for_ui(raw_new_ver) or raw_new_ver
        runtime.selected_version_by_campaign[campaign_id] = new_ver["version_id"]
        completed_job = runtime.jobs.complete_job(job_id, new_ver)
        snapshot = runtime.build_studio_snapshot(campaign_id=campaign_id, version_id=new_ver["version_id"])

        return {
            "structuredContent": {
                "job": completed_job,
                "version": new_ver,
                "studio": snapshot,
                "studio_state": snapshot,
            },
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Saved new content version `{new_ver['version_id']}` to "
                        f"`{new_ver['gcs']['bundle_gcs_uri']}` ({new_ver['diff_summary']})."
                    ),
                }
            ],
        }

    # Otherwise, delegate to async Gemini Omni + Nano Banana pipeline
    return await _handle_create_ad_campaign_job(runtime, _session_key, args)


async def _handle_upload_reference_asset(
    runtime: CreativeStudioRuntime, _session_key: str, args: dict[str, Any]
) -> dict[str, Any]:
    await runtime.ensure_seeded()
    campaign_id = str(args.get("campaign_id") or runtime.active_campaign_id or "acme_trailblazer_x1").strip()
    runtime.active_campaign_id = campaign_id
    filename = str(args.get("filename") or "uploaded_reference.svg").strip()
    asset_type = str(args.get("asset_type") or "image").strip().lower()
    description = str(
        args.get("description")
        or args.get("notes")
        or f"Reference {asset_type} uploaded to Acme Creative Studio"
    ).strip()

    raw_b64 = str(
        args.get("content_base64")
        or args.get("image_base64")
        or args.get("data_uri")
        or ""
    ).strip()
    content_text = str(args.get("content_text") or args.get("text_content") or "").strip()
    mime_type = str(args.get("mime_type") or args.get("content_type") or "").strip()
    data_uri_preview = ""

    if raw_b64:
        if raw_b64.startswith("data:"):
            header, _, b64_part = raw_b64.partition(",")
            if not mime_type and ";" in header:
                mime_type = header[5:].split(";", 1)[0]
            if header.startswith("data:image/"):
                data_uri_preview = raw_b64
            if ";base64" in header:
                raw_bytes = base64.b64decode(b64_part)
            else:
                raw_bytes = b64_part.encode("utf-8")
        else:
            raw_bytes = base64.b64decode(raw_b64)
    elif content_text:
        raw_bytes = content_text.encode("utf-8")
        if not mime_type:
            mime_type = "text/markdown" if filename.endswith(".md") else "text/plain"
        asset_type = "content"
    else:
        # Synthesize a branded reference image when invoked conversationally with a title/description
        svg_str = build_reference_product_svg(
            title=filename.rsplit(".", 1)[0].replace("_", " ").title(),
            subtitle=description,
            accent_a=str(args.get("accent_color") or "#0b57d0"),
            accent_b="#7c4dff",
            icon_text="📸" if asset_type == "image" else "📄",
        )
        raw_bytes = svg_str.encode("utf-8")
        mime_type = "image/svg+xml"
        if not filename.endswith(".svg"):
            filename = f"{filename}.svg"

    if not mime_type:
        if filename.lower().endswith(".png"):
            mime_type = "image/png"
        elif filename.lower().endswith((".jpg", ".jpeg")):
            mime_type = "image/jpeg"
        elif filename.lower().endswith(".svg"):
            mime_type = "image/svg+xml"
        else:
            mime_type = "text/plain"

    extracted_text = content_text
    if not extracted_text and mime_type.startswith("text/"):
        extracted_text = raw_bytes.decode("utf-8", errors="replace")

    asset_rec = await runtime.store.save_reference_asset(
        campaign_id=campaign_id,
        filename=filename,
        asset_type=asset_type,
        content_bytes=raw_bytes,
        mime_type=mime_type,
        description=description,
        extracted_text=extracted_text,
        data_uri_preview=data_uri_preview,
    )

    # Also append reference content to brand_brief if it's a brief/content asset
    if asset_type in ("content", "brief") and extracted_text:
        camp = runtime.store.ensure_campaign(campaign_id)
        existing_brief = camp.get("brand_brief") or ""
        if extracted_text not in existing_brief:
            camp["brand_brief"] = (existing_brief + f"\n\n--- Uploaded Reference ({filename}) ---\n{extracted_text}").strip()

    snapshot = runtime.build_studio_snapshot(campaign_id=campaign_id)
    return {
        "structuredContent": {
            "status": "uploaded",
            "reference": asset_rec,
            "uploaded_asset": asset_rec,
            "studio": snapshot,
            "studio_state": snapshot,
        },
        "content": [
            {
                "type": "text",
                "text": (
                    f"Uploaded reference {asset_type} `{asset_rec['filename']}` "
                    f"(`{asset_rec['asset_id']}`) to `{asset_rec['gcs_uri']}`."
                ),
            }
        ],
    }


async def _handle_get_studio_state(
    runtime: CreativeStudioRuntime, _session_key: str, args: dict[str, Any]
) -> dict[str, Any]:
    await runtime.ensure_seeded()
    campaign_id = args.get("campaign_id") or runtime.active_campaign_id
    version_id = args.get("version_id") or (f"v{args['version_number']}" if args.get("version_number") else None)
    if version_id and campaign_id:
        runtime.selected_version_by_campaign[str(campaign_id)] = str(version_id)
    snapshot = runtime.build_studio_snapshot(
        campaign_id=str(campaign_id) if campaign_id else None,
        version_id=str(version_id) if version_id else None,
    )
    return {
        "structuredContent": {
            **snapshot,
            "studio_state": snapshot,
        },
        "content": [
            {
                "type": "text",
                "text": (
                    f"Studio state for `{snapshot['active_campaign_id']}`: "
                    f"version `{snapshot['campaign']['viewed_version_id']}` "
                    f"({snapshot['campaign']['total_versions']} total versions in GCS, "
                    f"{len(snapshot['active_jobs'])} active job(s))."
                ),
            }
        ],
    }


async def _handle_list_active_jobs(
    runtime: CreativeStudioRuntime, _session_key: str, args: dict[str, Any]
) -> dict[str, Any]:
    await runtime.ensure_seeded()
    campaign_id = args.get("campaign_id")
    only_active = bool(args.get("only_active", False))
    jobs = runtime.jobs.list_jobs(
        campaign_id=str(campaign_id) if campaign_id else None,
        only_active=only_active,
    )
    notifications = runtime.jobs.list_notifications(
        campaign_id=str(campaign_id) if campaign_id else None,
        unread_only=False,
    )
    return {
        "structuredContent": {
            "jobs": jobs,
            "notifications": notifications,
            "active_count": sum(1 for j in jobs if j["status"] in ("queued", "running")),
        },
        "content": [
            {
                "type": "text",
                "text": f"Found {len(jobs)} backend job(s) and {len(notifications)} notification(s).",
            }
        ],
    }


async def _handle_get_job_status(
    runtime: CreativeStudioRuntime, _session_key: str, args: dict[str, Any]
) -> dict[str, Any]:
    job_id = str(args.get("job_id") or "").strip()
    if not job_id:
        raise McpToolError("`job_id` is required to inspect a backend job.")
    job = runtime.jobs.get_job(job_id)
    if not job:
        raise McpToolError(f"Job `{job_id}` was not found.")
    job_out = dict(job)
    if job_out.get("result_version_id") and not job_out.get("result_version"):
        ver_obj = runtime.store.get_version_sync(
            job_out.get("campaign_id", runtime.active_campaign_id),
            job_out["result_version_id"],
        )
        if ver_obj:
            job_out["result_version"] = {
                "version_id": ver_obj["version_id"],
                "version_number": ver_obj["version_number"],
                "gcs_uri": ver_obj["gcs"]["bundle_gcs_uri"],
            }
    return {
        "structuredContent": {"job": job_out},
        "content": [
            {
                "type": "text",
                "text": (
                    f"Job `{job_id}` ({job_out['title']}): status=`{job_out['status']}`, "
                    f"progress={job_out['progress_pct']}%, stage='{job_out['current_stage']}', "
                    f"result_version=`{job_out.get('result_version_id') or 'pending'}`."
                ),
            }
        ],
    }


async def _handle_acknowledge_job_notification(
    runtime: CreativeStudioRuntime, _session_key: str, args: dict[str, Any]
) -> dict[str, Any]:
    notif_ids = args.get("notification_ids") or args.get("notification_id")
    if isinstance(notif_ids, str):
        notif_ids = [notif_ids]
    ack_all = bool(args.get("acknowledge_all", False)) or (notif_ids is None)
    campaign_id = args.get("campaign_id")
    count = runtime.jobs.acknowledge_notifications(
        notification_ids=notif_ids if isinstance(notif_ids, list) else None,
        campaign_id=str(campaign_id) if campaign_id else None,
        acknowledge_all=ack_all,
    )
    snapshot = runtime.build_studio_snapshot(
        campaign_id=str(campaign_id) if campaign_id else None
    )
    return {
        "structuredContent": {
            "acknowledged_count": count,
            "unread_notifications": runtime.jobs.list_notifications(unread_only=True),
            "studio_state": snapshot,
        },
        "content": [
            {"type": "text", "text": f"Acknowledged {count} notification(s)."}
        ],
    }


async def _handle_list_content_versions(
    runtime: CreativeStudioRuntime, _session_key: str, args: dict[str, Any]
) -> dict[str, Any]:
    await runtime.ensure_seeded()
    campaign_id = str(args.get("campaign_id") or runtime.active_campaign_id or "acme_trailblazer_x1").strip()
    snapshot = runtime.build_studio_snapshot(campaign_id=campaign_id)
    versions = snapshot["versions"]
    return {
        "structuredContent": {
            "campaign_id": campaign_id,
            "gcs_bucket": runtime.store.bucket_name,
            "total_versions": len(versions),
            "versions": versions,
            "studio_state": snapshot,
        },
        "content": [
            {
                "type": "text",
                "text": (
                    f"Found {len(versions)} content version(s) for `{campaign_id}` in "
                    f"`gs://{runtime.store.bucket_name}/campaigns/{campaign_id}/versions/`: "
                    + ", ".join(f"{v['version_id']} ({v['author_action']})" for v in versions)
                ),
            }
        ],
    }


async def _handle_get_content_version(
    runtime: CreativeStudioRuntime, _session_key: str, args: dict[str, Any]
) -> dict[str, Any]:
    await runtime.ensure_seeded()
    campaign_id = str(args.get("campaign_id") or runtime.active_campaign_id or "acme_trailblazer_x1").strip()
    raw_vid = args.get("version_id") or args.get("version_number")
    version_id = str(raw_vid).strip() if raw_vid is not None else None
    ver = runtime.store.get_version_sync(campaign_id, version_id)
    if not ver:
        raise McpToolError(f"Version `{version_id}` not found for campaign `{campaign_id}`.")
    norm_ver = runtime._normalize_version_for_ui(ver) or ver
    runtime.selected_version_by_campaign[campaign_id] = norm_ver["version_id"]
    snapshot = runtime.build_studio_snapshot(campaign_id=campaign_id, version_id=norm_ver["version_id"])
    return {
        "structuredContent": {
            "version": norm_ver,
            "studio": snapshot,
            "studio_state": snapshot,
        },
        "content": [
            {
                "type": "text",
                "text": (
                    f"Loaded content version `{norm_ver['version_id']}` for `{campaign_id}` "
                    f"from `{norm_ver['gcs']['bundle_gcs_uri']}`.\n"
                    f"- **Headline**: {norm_ver['ad_copy'].get('headline')}\n"
                    f"- **CTA**: {norm_ver['ad_copy'].get('cta_text')}\n"
                    f"- **Diff Summary**: {norm_ver['diff_summary']}"
                ),
            }
        ],
    }


async def _handle_compare_content_versions(
    runtime: CreativeStudioRuntime, _session_key: str, args: dict[str, Any]
) -> dict[str, Any]:
    await runtime.ensure_seeded()
    campaign_id = str(args.get("campaign_id") or runtime.active_campaign_id or "acme_trailblazer_x1").strip()
    base_vid = str(args.get("base_version_id") or args.get("version_a") or "v1").strip()
    target_vid = str(args.get("target_version_id") or args.get("version_b") or "").strip()
    if not target_vid:
        versions = runtime.store.list_versions_sync(campaign_id)
        target_vid = versions[0]["version_id"] if versions else "v1"

    diff = runtime.store.compare_versions_sync(campaign_id, base_vid, target_vid)
    if not diff:
        raise McpToolError(
            f"Could not compare versions `{base_vid}` and `{target_vid}` for `{campaign_id}`."
        )

    # Add unified_diff and field_changes aliases for UI & test harness
    field_changes = []
    unified_lines = [
        f"--- {diff['base_version']['version_id']} ({diff['base_version']['gcs_uri']})",
        f"+++ {diff['target_version']['version_id']} ({diff['target_version']['gcs_uri']})",
    ]
    for fd in diff.get("field_diffs", []):
        if fd.get("changed"):
            field_changes.append(
                {
                    "field": fd["field"],
                    "version_a": fd["base_value"],
                    "version_b": fd["target_value"],
                }
            )
            unified_lines.append(f"@@ {fd['field']} @@")
            unified_lines.append(f"- {fd['base_value']}")
            unified_lines.append(f"+ {fd['target_value']}")

    diff["total_fields_changed"] = diff["changed_fields_count"]
    diff["field_changes"] = field_changes
    diff["unified_diff"] = "\n".join(unified_lines)

    return {
        "structuredContent": {
            **diff,
            "comparison": diff,
        },
        "content": [
            {
                "type": "text",
                "text": (
                    f"Compared `{diff['base_version']['version_id']}` ↔ "
                    f"`{diff['target_version']['version_id']}` for `{campaign_id}`: "
                    f"{diff['changed_fields_count']} of {diff['total_fields_compared']} fields changed."
                ),
            }
        ],
    }


async def _handle_restore_content_version(
    runtime: CreativeStudioRuntime, _session_key: str, args: dict[str, Any]
) -> dict[str, Any]:
    await runtime.ensure_seeded()
    campaign_id = str(args.get("campaign_id") or runtime.active_campaign_id or "acme_trailblazer_x1").strip()
    raw_vid = args.get("version_id") or args.get("version_number") or "v1"
    target_vid = str(raw_vid).strip()
    source_ver = runtime.store.get_version_sync(campaign_id, target_vid)
    if not source_ver:
        raise McpToolError(f"Version `{target_vid}` not found in campaign `{campaign_id}`.")

    camp = runtime.store.ensure_campaign(campaign_id)
    next_v_num = len(camp.get("versions", [])) + 1
    next_label = f"v{next_v_num}"

    # Re-stamp visual SVG badge with the new restored version label
    vis_copy = dict(source_ver["visual_creative"])
    ref_images = [a for a in camp.get("reference_assets", []) if a.get("asset_type") == "image"]
    ref_uri = ref_images[-1].get("data_uri_preview", "") if ref_images else ""
    svg_markup = build_nano_banana_creative_svg(
        headline=source_ver["ad_copy"].get("headline", ""),
        subheadline=source_ver["ad_copy"].get("subheadline", ""),
        cta_text=source_ver["ad_copy"].get("cta_text", ""),
        product_name=camp["product_name"],
        aspect_ratio=vis_copy.get("aspect_ratio", "1:1"),
        color_palette=vis_copy.get("color_palette"),
        reference_image_uri=ref_uri,
        version_label=next_label,
        visual_style_tag=f"Restored from {source_ver['version_id']}",
    )
    vis_copy["svg_markup"] = svg_markup
    vis_copy["image_data_uri"] = (
        "data:image/svg+xml;base64,"
        + base64.b64encode(svg_markup.encode("utf-8")).decode("ascii")
    )

    job_info = runtime.jobs.create_job(
        campaign_id=campaign_id,
        job_type="restore_version",
        title=f"Restore {source_ver['version_id']} -> {next_label}",
        prompt_summary=f"Restored content version {source_ver['version_id']} from GCS bucket",
    )
    raw_new_ver = await runtime.store.create_content_version(
        campaign_id=campaign_id,
        ad_copy_data=source_ver["ad_copy"],
        visual_data=vis_copy,
        job_id=job_info["job_id"],
        author_action=f"Restored from {source_ver['version_id']}",
        prompt_used=f"Rollback/restore to {source_ver['version_id']}",
        parent_version_id=source_ver["version_id"],
    )
    new_ver = runtime._normalize_version_for_ui(raw_new_ver) or raw_new_ver
    new_ver["restored_from_version"] = source_ver["version_number"]
    runtime.selected_version_by_campaign[campaign_id] = new_ver["version_id"]
    runtime.jobs.complete_job(job_info["job_id"], new_ver)
    snapshot = runtime.build_studio_snapshot(campaign_id=campaign_id, version_id=new_ver["version_id"])

    return {
        "structuredContent": {
            "restored_version": new_ver,
            "studio": snapshot,
            "studio_state": snapshot,
        },
        "content": [
            {
                "type": "text",
                "text": (
                    f"Restored `{source_ver['version_id']}` as new immutable version "
                    f"`{new_ver['version_id']}` in `{new_ver['gcs']['bundle_gcs_uri']}`."
                ),
            }
        ],
    }


# ---------------------------------------------------------------------------
# Tool Registry (12 Tools with SEP-1865 / MCP-Apps UI Metadata)
# ---------------------------------------------------------------------------

_TOOLS: list[dict[str, Any]] = [
    {
        "name": "open_creative_studio",
        "description": (
            "Open the interactive Acme Inc. Creative Studio MCP App in the side panel "
            "to create multimodal ad copy with Gemini Omni and visual creatives with "
            "Nano Banana, upload reference images/content, monitor active backend jobs, "
            "and browse GCS content versions. Never route or transfer to canvas_agent."
        ),
        "_meta": _build_ui_meta(visibility=["model", "app"], is_widget=True, preferred_mode="pip"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {
                    "type": "string",
                    "description": "Campaign ID (e.g. 'acme_trailblazer_x1', 'acme_pulse_espresso', 'acme_cloudsync_ai').",
                },
                "version_id": {
                    "type": "string",
                    "description": "Optional specific GCS version to view (e.g. 'v1', 'v2').",
                },
            },
        },
        "handler": _handle_open_creative_studio,
    },
    {
        "name": "create_ad_campaign_job",
        "description": (
            "Start an asynchronous backend job (<2s response) that synthesizes ad copy "
            "with Gemini Omni and visual creatives with Nano Banana using uploaded reference "
            "images and brand content, saving the resulting version to the GCS bucket. "
            "Never route or transfer to canvas_agent."
        ),
        "_meta": _build_ui_meta(visibility=["model", "app"], is_widget=True, preferred_mode="pip"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "prompt_instructions": {
                    "type": "string",
                    "description": "Creative direction, ad copy angle, or visual scene prompt.",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["1:1", "16:9", "9:16"],
                    "default": "1:1",
                },
                "tone": {
                    "type": "string",
                    "description": "Brand voice tone (e.g. 'Bold & High-Converting', 'Executive & Metric-Driven', 'Warm Luxury').",
                },
                "product_name": {"type": "string"},
                "brand_brief": {"type": "string"},
                "wait_for_completion": {"type": "boolean"},
            },
        },
        "handler": _handle_create_ad_campaign_job,
    },
    {
        "name": "refine_ad_copy_job",
        "description": (
            "Refine ad copy or visual creative parameters and commit a new immutable "
            "content version (vN+1) to the GCS bucket."
        ),
        "_meta": _build_ui_meta(visibility=["model", "app"]),
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "base_version_id": {"type": "string"},
                "headline": {"type": "string"},
                "subheadline": {"type": "string"},
                "primary_copy": {"type": "string"},
                "cta_text": {"type": "string"},
                "visual_prompt": {"type": "string"},
                "aspect_ratio": {"type": "string"},
                "revision_note": {"type": "string"},
                "prompt_instructions": {"type": "string"},
            },
        },
        "handler": _handle_refine_ad_copy_job,
    },
    {
        "name": "upload_reference_asset",
        "description": (
            "Upload a reference image (product photo, style moodboard) or reference "
            "content (brand guidelines, creative brief) to the active campaign and "
            "persist it in the GCS bucket."
        ),
        "_meta": _build_ui_meta(visibility=["model", "app"]),
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "filename": {"type": "string"},
                "asset_type": {
                    "type": "string",
                    "enum": ["image", "content", "brief"],
                },
                "description": {"type": "string"},
                "content_base64": {
                    "type": "string",
                    "description": "Base64 or Data URI of the uploaded image or file.",
                },
                "content_text": {
                    "type": "string",
                    "description": "Text or Markdown reference content / creative brief.",
                },
                "mime_type": {"type": "string"},
            },
            "required": ["filename"],
        },
        "handler": _handle_upload_reference_asset,
    },
    {
        "name": "get_studio_state",
        "description": (
            "Poll the current Creative Studio state, including active campaign, current "
            "GCS content version, reference assets, running backend jobs, stage percentages, "
            "and unread completion notifications."
        ),
        "_meta": _build_ui_meta(visibility=["app", "model"]),
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "version_id": {"type": "string"},
            },
        },
        "handler": _handle_get_studio_state,
    },
    {
        "name": "list_active_jobs",
        "description": (
            "List active, queued, and recently completed backend jobs and user notifications."
        ),
        "_meta": _build_ui_meta(visibility=["model", "app"]),
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "only_active": {"type": "boolean"},
            },
        },
        "handler": _handle_list_active_jobs,
    },
    {
        "name": "get_job_status",
        "description": (
            "Get the real-time execution status, stage progress percentage, stage log, "
            "and resulting GCS content version for a specific backend job ID."
        ),
        "_meta": _build_ui_meta(visibility=["model", "app"]),
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
            },
            "required": ["job_id"],
        },
        "handler": _handle_get_job_status,
    },
    {
        "name": "acknowledge_job_notification",
        "description": "Dismiss or mark backend job completion notifications as read.",
        "_meta": _build_ui_meta(visibility=["app"]),
        "inputSchema": {
            "type": "object",
            "properties": {
                "notification_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "campaign_id": {"type": "string"},
                "acknowledge_all": {"type": "boolean"},
            },
        },
        "handler": _handle_acknowledge_job_notification,
    },
    {
        "name": "list_content_versions",
        "description": (
            "List all saved immutable versions (v1, v2, v3, ...) of the campaign's ad copy "
            "and Nano Banana visuals stored in the GCS bucket."
        ),
        "_meta": _build_ui_meta(visibility=["model", "app"]),
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
            },
        },
        "handler": _handle_list_content_versions,
    },
    {
        "name": "get_content_version",
        "description": (
            "Fetch and view a specific content version (e.g., 'v1', 'v2') from the GCS bucket."
        ),
        "_meta": _build_ui_meta(visibility=["model", "app"]),
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "version_id": {"type": "string"},
            },
            "required": ["version_id"],
        },
        "handler": _handle_get_content_version,
    },
    {
        "name": "compare_content_versions",
        "description": (
            "Compare two saved content versions (e.g. v1 vs v2) from the GCS bucket "
            "and return a structured field-by-field diff across ad copy, channel variants, "
            "and Nano Banana visual creative settings."
        ),
        "_meta": _build_ui_meta(visibility=["model", "app"]),
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "base_version_id": {"type": "string"},
                "target_version_id": {"type": "string"},
            },
            "required": ["base_version_id", "target_version_id"],
        },
        "handler": _handle_compare_content_versions,
    },
    {
        "name": "restore_content_version",
        "description": (
            "Restore a historical content version from the GCS bucket as the new active "
            "version (vN+1) while preserving full version lineage."
        ),
        "_meta": _build_ui_meta(visibility=["model", "app"]),
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "version_id": {"type": "string"},
            },
            "required": ["version_id"],
        },
        "handler": _handle_restore_content_version,
    },
]

_TOOLS_BY_NAME: dict[str, dict[str, Any]] = {t["name"]: t for t in _TOOLS}


def _tool_descriptor(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": tool["name"],
        "title": tool.get("title") or tool["name"].replace("_", " ").title(),
        "description": tool["description"],
        "inputSchema": tool["inputSchema"],
        "icon": "palette",
        "icon_url": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/palette/default/24px.svg",
        "_meta": tool["_meta"],
        "meta": tool["_meta"],
    }


async def dispatch_mcp_method(
    runtime: CreativeStudioRuntime,
    session_key_or_method: str,
    method_or_params: str | dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatches a single JSON-RPC 2.0 MCP method call.

    Supports both `(runtime, method, params)` and `(runtime, session_key, method, params)`.
    """
    if isinstance(method_or_params, dict) or method_or_params is None:
        session_key = "default_session"
        method = session_key_or_method
        resolved_params = method_or_params if isinstance(method_or_params, dict) else {}
    else:
        session_key = session_key_or_method
        method = str(method_or_params)
        resolved_params = params if isinstance(params, dict) else {}

    if method == "initialize":
        requested = str(resolved_params.get("protocolVersion") or "")
        version = (
            requested
            if requested in SUPPORTED_PROTOCOL_VERSIONS
            else MCP_PROTOCOL_VERSION
        )
        return {
            "protocolVersion": version,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
            },
            "serverInfo": {
                "name": "acme-creative-studio-mcp",
                "title": "Acme Inc. Creative Studio (Gemini Omni + Nano Banana)",
                "version": "1.0.0",
                "icon": "palette",
                "icon_url": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/palette/default/24px.svg",
            },
            "instructions": (
                "CRITICAL: Always use `open_creative_studio` or `create_ad_campaign_job` "
                "whenever the user asks to open the Acme Inc. Creative Studio, create ad copy "
                "with Gemini Omni and Nano Banana, upload reference images/content, track active "
                "backend jobs, or inspect/compare content versions in the GCS bucket. "
                "Do NOT transfer to Canvas, do NOT call canvas_agent, and do NOT create a "
                "markdown document in place of the interactive Creative Studio workspace."
            ),
        }

    if method == "ping":
        return {}

    if method == "tools/list":
        return {"tools": [_tool_descriptor(t) for t in _TOOLS]}

    if method == "resources/list":
        return {
            "resources": [
                {
                    "uri": WIDGET_URI,
                    "name": "Acme Inc. Creative Studio Workspace",
                    "description": (
                        "Interactive multimodal ad copy and visual creative studio powered by "
                        "Gemini Omni and Nano Banana with reference uploads, live job tracking, "
                        "and GCS content version history."
                    ),
                    "mimeType": WIDGET_MIME,
                    "_meta": RESOURCE_META,
                }
            ]
        }

    if method == "resources/read":
        await runtime.ensure_seeded()
        raw_uri = str(resolved_params.get("uri") or "")
        base_req_uri = raw_uri.split("#", 1)[0].split("?", 1)[0]
        if base_req_uri not in (
            WIDGET_URI,
            "ui://acme/creative-studio.html",
            "ui://acme/creative_studio.html",
        ):
            raise _RpcError(INVALID_PARAMS, f"Unknown resource URI: {raw_uri!r}")
        return {
            "contents": [
                {
                    "uri": WIDGET_URI,
                    "mimeType": WIDGET_MIME,
                    "text": _load_widget_html(runtime),
                    "_meta": RESOURCE_META,
                }
            ]
        }

    if method == "tools/call":
        name = str(resolved_params.get("name") or "")
        tool = _TOOLS_BY_NAME.get(name)
        if tool is None and "__" in name:
            # Strip Dolphin / AgentFlow custom agent namespace prefix:
            # custom_mcp_<connector_id>_agent__<tool_name>
            tool = _TOOLS_BY_NAME.get(name.rsplit("__", 1)[-1])
        if tool is None:
            raise _RpcError(INVALID_PARAMS, f"Unknown tool: {name!r}")

        args = resolved_params.get("arguments")
        if not isinstance(args, dict):
            args = {}

        try:
            result = await tool["handler"](runtime, session_key, args)
        except McpToolError as err:
            return {"content": [{"type": "text", "text": str(err)}], "isError": True}
        except Exception as err:
            return {
                "content": [{"type": "text", "text": f"Tool {name} failed: {err}"}],
                "isError": True,
            }
        result.setdefault("isError", False)
        return result

    raise _RpcError(METHOD_NOT_FOUND, f"Unknown method: {method!r}")


def register_mcp_routes(app: Any, runtime: CreativeStudioRuntime) -> None:
    """Registers `/mcp`, `/download/{token}`, and `/api/upload-reference` routes."""

    async def mcp_endpoint(request: Request) -> Response:
        if request.method == "DELETE":
            return Response(status_code=204)
        if request.method == "GET":
            return Response(status_code=405, headers={"Allow": "POST, DELETE"})

        raw_body = await request.body()
        try:
            body = json.loads(raw_body)
        except Exception:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": PARSE_ERROR, "message": "Invalid JSON"},
                },
                status_code=400,
            )

        if isinstance(body, list) and not body:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": INVALID_REQUEST, "message": "Empty batch"},
                },
                status_code=400,
            )

        session_key = (
            request.headers.get("mcp-session-id")
            or request.headers.get("Mcp-Session-Id")
            or ""
        ).strip()
        batch = body if isinstance(body, list) else [body]
        responses: list[dict[str, Any]] = []
        new_session_id: str | None = None

        for item in batch:
            if not isinstance(item, dict) or item.get("jsonrpc") != "2.0":
                responses.append(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": INVALID_REQUEST,
                            "message": "Expected a JSON-RPC 2.0 request object",
                        },
                    }
                )
                continue

            method = str(item.get("method") or "")
            req_id = item.get("id")
            params = item.get("params")
            if not isinstance(params, dict):
                params = {}

            if method == "initialize" and not session_key:
                new_session_id = uuid.uuid4().hex
                session_key = new_session_id

            if req_id is None:
                # JSON-RPC Notification (e.g., notifications/initialized)
                continue

            try:
                result = await dispatch_mcp_method(
                    runtime, session_key, method, params
                )
                responses.append({"jsonrpc": "2.0", "id": req_id, "result": result})
            except _RpcError as err:
                responses.append(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": err.code, "message": err.message},
                    }
                )
            except Exception as err:
                responses.append(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": INTERNAL_ERROR, "message": str(err)},
                    }
                )

        headers: dict[str, str] = {}
        if new_session_id:
            headers["Mcp-Session-Id"] = new_session_id

        if not responses:
            return Response(status_code=202, headers=headers)

        payload = responses if isinstance(body, list) else responses[0]
        return Response(
            content=json.dumps(payload),
            media_type="application/json",
            headers=headers,
        )

    async def download_handler(request: Request) -> Response:
        token = str(request.path_params.get("token", ""))
        entry = runtime.store.get_download_by_token(token)
        if not entry:
            return Response(
                "Download link is invalid or has expired.",
                status_code=404,
                media_type="text/plain",
            )
        disposition = (
            "attachment"
            if request.query_params.get("download") == "1"
            else "inline"
        )
        return Response(
            content=entry["bytes"],
            media_type=entry["mime_type"],
            headers={
                "Content-Disposition": f'{disposition}; filename="{entry["filename"]}"',
                "Cache-Control": "private, no-store",
                "Access-Control-Allow-Origin": "*",
            },
        )

    async def upload_reference_handler(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response(status_code=204)
        await runtime.ensure_seeded()
        content_type = (request.headers.get("content-type") or "").lower()
        if "multipart/form-data" in content_type:
            form = await request.form()
            file_item = form.get("file")
            campaign_id = str(form.get("campaign_id") or runtime.active_campaign_id)
            asset_type = str(form.get("asset_type") or "image")
            description = str(form.get("description") or "")
            if file_item is None or not hasattr(file_item, "read"):
                return JSONResponse({"error": "Missing file upload"}, status_code=400)
            raw_bytes = await file_item.read()  # type: ignore
            filename = getattr(file_item, "filename", "upload.bin") or "upload.bin"
            mime_type = getattr(file_item, "content_type", "") or "application/octet-stream"
            b64_str = base64.b64encode(raw_bytes).decode("ascii")
            res = await _handle_upload_reference_asset(
                runtime,
                "http_upload",
                {
                    "campaign_id": campaign_id,
                    "filename": filename,
                    "asset_type": asset_type,
                    "description": description,
                    "content_base64": b64_str,
                    "mime_type": mime_type,
                },
            )
            return JSONResponse(res["structuredContent"])
        else:
            payload = await request.json()
            res = await _handle_upload_reference_asset(runtime, "http_upload", payload)
            return JSONResponse(res["structuredContent"])

    app.add_route("/mcp", mcp_endpoint, methods=["POST", "GET", "DELETE"])
    app.add_route("/download/{token}", download_handler, methods=["GET"])
    app.add_route(
        "/api/upload-reference",
        upload_reference_handler,
        methods=["POST", "OPTIONS"],
    )


# Default module-level runtime instance
studio_runtime = CreativeStudioRuntime()

