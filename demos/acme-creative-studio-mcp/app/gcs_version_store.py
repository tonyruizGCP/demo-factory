"""Google Cloud Storage (GCS) Content Version Store & Reference Asset Repository.

Persists every Acme Inc. Creative Studio campaign iteration as an immutable version
(`v1`, `v2`, `v3`, ...) inside a GCS bucket (`GCS_CREATIVE_BUCKET`) alongside a
synchronized in-memory & local filesystem mirror so the studio operates seamlessly
in both live Cloud Run + GCS environments and offline / unit-test sandboxes.

GCS Object Layout:
  gs://<bucket>/campaigns/<campaign_id>/manifest.json
  gs://<bucket>/campaigns/<campaign_id>/references/<asset_id>_<filename>
  gs://<bucket>/campaigns/<campaign_id>/versions/v<N>/bundle.json
  gs://<bucket>/campaigns/<campaign_id>/versions/v<N>/ad_copy.md
  gs://<bucket>/campaigns/<campaign_id>/versions/v<N>/creative.svg
"""

from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import json
import os
import re
import secrets
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_filename(name: str, default: str = "asset.bin") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.basename(name or default)).strip("._")
    return cleaned or default


class GcsVersionStore:
    """Manages GCS-backed campaign versions, reference assets, diffs, and download tokens."""

    def __init__(
        self,
        bucket_name: str | None = None,
        local_mirror_dir: str | Path | None = None,
    ) -> None:
        self._lock = threading.RLock()
        project_id = (
            os.environ.get("GCP_PROJECT")
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or "truiz-agy-demo"
        )
        default_bucket = f"{project_id}-acme-creative-studio-assets"
        self.bucket_name = (
            bucket_name
            or os.environ.get("GCS_CREATIVE_BUCKET")
            or default_bucket
        ).strip()

        base_dir = Path(__file__).resolve().parent.parent / ".gcs_local_mirror"
        self.local_mirror_dir = Path(local_mirror_dir) if local_mirror_dir else base_dir
        self.local_mirror_dir.mkdir(parents=True, exist_ok=True)

        # In-memory index keyed by campaign_id
        self._campaigns: dict[str, dict[str, Any]] = {}
        # Signed download token cache (2h TTL, modeled on Cooley MTS session_store.py)
        self._download_tokens: dict[str, dict[str, Any]] = {}
        self._gcs_available: bool | None = None

    # ------------------------------------------------------------------
    # GCS Client Helpers (Fail-open with Local Mirror)
    # ------------------------------------------------------------------

    def _write_to_gcs_sync(
        self, object_path: str, data: bytes, content_type: str
    ) -> tuple[bool, str]:
        """Writes object bytes to local mirror and attempts live GCS upload if enabled."""
        # Always write to local mirror for deterministic fast reads & offline resilience
        local_path = self.local_mirror_dir / object_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)

        gcs_uri = f"gs://{self.bucket_name}/{object_path}"
        if os.environ.get("DISABLE_LIVE_GCS", "").lower() in ("1", "true", "yes"):
            return False, gcs_uri

        try:
            from google.cloud import storage  # type: ignore

            project_id = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
            client = storage.Client(project=project_id) if project_id else storage.Client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(object_path)
            blob.upload_from_string(data, content_type=content_type)
            self._gcs_available = True
            return True, gcs_uri
        except Exception as exc:
            # Fail-open per Cooley MTS review_state.py contract: never fail user turn
            self._gcs_available = False
            return False, f"{gcs_uri} (staged in local mirror: {type(exc).__name__})"

    async def _write_object(
        self, object_path: str, data: bytes, content_type: str
    ) -> dict[str, Any]:
        synced, uri_note = await asyncio.to_thread(
            self._write_to_gcs_sync, object_path, data, content_type
        )
        gcs_uri = f"gs://{self.bucket_name}/{object_path}"
        console_url = (
            f"https://console.cloud.google.com/storage/browser/_details/"
            f"{self.bucket_name}/{object_path}"
        )
        storage_url = f"https://storage.cloud.google.com/{self.bucket_name}/{object_path}"
        return {
            "bucket": self.bucket_name,
            "object_path": object_path,
            "gcs_uri": gcs_uri,
            "console_url": console_url,
            "storage_url": storage_url,
            "live_gcs_synced": synced,
            "status_note": uri_note,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()[:16],
        }

    # ------------------------------------------------------------------
    # Signed Download Tokens (Sandbox Escape via /download/{token})
    # ------------------------------------------------------------------

    def mint_download_token(
        self,
        data: bytes,
        filename: str,
        mime_type: str = "application/octet-stream",
        ttl_s: int = 7200,
    ) -> str:
        token = secrets.token_urlsafe(24)
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._download_tokens.items() if v["exp"] < now]
            for k in expired:
                self._download_tokens.pop(k, None)
            self._download_tokens[token] = {
                "bytes": data,
                "filename": filename,
                "mime_type": mime_type,
                "exp": now + ttl_s,
            }
        return token

    def get_download_by_token(self, token: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self._download_tokens.get(token)
            if not entry:
                return None
            if entry["exp"] < time.time():
                self._download_tokens.pop(token, None)
                return None
            return entry

    # ------------------------------------------------------------------
    # Campaign & Reference Asset Management
    # ------------------------------------------------------------------

    def ensure_campaign(
        self,
        campaign_id: str,
        name: str | None = None,
        product_name: str | None = None,
        brand_brief: str | None = None,
        target_audience: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            camp = self._campaigns.get(campaign_id)
            if camp is None:
                camp = {
                    "campaign_id": campaign_id,
                    "name": name or f"Acme Campaign ({campaign_id})",
                    "customer": "Acme Inc.",
                    "product_name": product_name or "Acme Flagship Product",
                    "brand_brief": brand_brief or "",
                    "target_audience": target_audience or "Enterprise & Consumer Decision Makers",
                    "created_at": _utc_iso(),
                    "updated_at": _utc_iso(),
                    "active_version_id": None,
                    "reference_assets": [],
                    "versions": [],
                }
                self._campaigns[campaign_id] = camp
            else:
                if name:
                    camp["name"] = name
                if product_name:
                    camp["product_name"] = product_name
                if brand_brief is not None:
                    camp["brand_brief"] = brand_brief
                if target_audience:
                    camp["target_audience"] = target_audience
                camp["updated_at"] = _utc_iso()
            return camp

    async def save_reference_asset(
        self,
        campaign_id: str,
        filename: str,
        asset_type: str,
        content_bytes: bytes,
        mime_type: str,
        description: str = "",
        extracted_text: str = "",
        data_uri_preview: str = "",
    ) -> dict[str, Any]:
        """Stores a reference image or reference content file in GCS and attaches to campaign."""
        camp = self.ensure_campaign(campaign_id)
        safe_name = _safe_filename(filename, "reference.bin")
        digest = hashlib.sha256(content_bytes).hexdigest()[:12]
        asset_id = f"ref_{int(time.time())}_{digest[:6]}"
        object_path = f"campaigns/{campaign_id}/references/{asset_id}_{safe_name}"

        gcs_meta = await self._write_object(object_path, content_bytes, mime_type)
        dl_token = self.mint_download_token(content_bytes, safe_name, mime_type)

        if not data_uri_preview and mime_type.startswith("image/") and len(content_bytes) <= 2_500_000:
            b64 = base64.b64encode(content_bytes).decode("ascii")
            data_uri_preview = f"data:{mime_type};base64,{b64}"

        asset_record: dict[str, Any] = {
            "asset_id": asset_id,
            "campaign_id": campaign_id,
            "filename": safe_name,
            "asset_type": asset_type,  # "image" | "content" | "brief"
            "mime_type": mime_type,
            "size_bytes": len(content_bytes),
            "sha256": digest,
            "description": description or f"Uploaded {asset_type}: {safe_name}",
            "extracted_text": extracted_text[:10000] if extracted_text else "",
            "data_uri_preview": data_uri_preview,
            "gcs_uri": gcs_meta["gcs_uri"],
            "console_url": gcs_meta["console_url"],
            "storage_url": gcs_meta["storage_url"],
            "download_url": f"/download/{dl_token}",
            "live_gcs_synced": gcs_meta["live_gcs_synced"],
            "uploaded_at": _utc_iso(),
        }

        with self._lock:
            # Replace if identical sha256 already exists in campaign
            existing = [
                a for a in camp["reference_assets"] if a.get("sha256") != digest
            ]
            existing.append(asset_record)
            camp["reference_assets"] = existing
            camp["updated_at"] = _utc_iso()

        await self._sync_campaign_manifest(campaign_id)
        return copy.deepcopy(asset_record)

    # ------------------------------------------------------------------
    # Immutable Content Versioning in GCS (v1, v2, v3, ...)
    # ------------------------------------------------------------------

    async def create_content_version(
        self,
        campaign_id: str,
        ad_copy_data: dict[str, Any],
        visual_data: dict[str, Any],
        job_id: str | None = None,
        author_action: str = "Generated via Gemini Omni + Nano Banana",
        prompt_used: str = "",
        parent_version_id: str | None = None,
    ) -> dict[str, Any]:
        """Creates a new immutable content version (v1, v2, ...) and writes artifacts to GCS."""
        camp = self.ensure_campaign(campaign_id)
        with self._lock:
            version_number = len(camp["versions"]) + 1
            version_id = f"v{version_number}"
            if parent_version_id is None and camp["versions"]:
                parent_version_id = camp["versions"][-1]["version_id"]

            prev_version = self.get_version_sync(campaign_id, parent_version_id) if parent_version_id else None
            reference_snapshot = [
                {
                    "asset_id": r["asset_id"],
                    "filename": r["filename"],
                    "asset_type": r["asset_type"],
                    "gcs_uri": r["gcs_uri"],
                }
                for r in camp.get("reference_assets", [])
            ]

        diff_summary = self._compute_change_summary(prev_version, ad_copy_data, visual_data, author_action)

        # Build Markdown deliverable for ad_copy.md in GCS
        md_lines = [
            f"# {camp['name']} — Content Version {version_id}",
            f"- **Customer**: Acme Inc.",
            f"- **Campaign ID**: `{campaign_id}`",
            f"- **Version**: `{version_id}` (Parent: `{parent_version_id or 'root'}`)",
            f"- **Created At**: `{_utc_iso()}`",
            f"- **Copy Model**: `{ad_copy_data.get('model_used', 'gemini-omni-flash-preview')}`",
            f"- **Visual Model**: `{visual_data.get('model_used', 'gemini-3.1-flash-image-preview (Nano Banana)')}`",
            "",
            "## 1. Core Ad Copy (Gemini Omni)",
            f"### Headline\n{ad_copy_data.get('headline', '')}",
            f"### Subheadline\n{ad_copy_data.get('subheadline', '')}",
            f"### Primary Copy\n{ad_copy_data.get('primary_copy', '')}",
            f"### Call to Action\n`{ad_copy_data.get('cta_text', '')}`",
            "",
            "## 2. Multi-Channel Ad Variations",
        ]
        for ch_key, ch_val in (ad_copy_data.get("channel_variants") or {}).items():
            md_lines.append(f"### {ch_key.replace('_', ' ').title()}\n{ch_val}\n")

        md_lines.extend([
            "## 3. Nano Banana Visual Creative Spec",
            f"- **Visual Prompt**: {visual_data.get('visual_prompt', '')}",
            f"- **Aspect Ratio**: {visual_data.get('aspect_ratio', '1:1')}",
            f"- **Color Palette**: {', '.join(visual_data.get('color_palette', []))}",
            f"- **Composition Notes**: {visual_data.get('composition_notes', '')}",
        ])
        ad_copy_md_bytes = "\n".join(md_lines).encode("utf-8")

        # Visual SVG/PNG bytes for GCS
        svg_markup = visual_data.get("svg_markup") or ""
        image_bytes = svg_markup.encode("utf-8")
        image_ext = "svg"
        image_mime = "image/svg+xml"
        if visual_data.get("raw_image_bytes"):
            image_bytes = visual_data["raw_image_bytes"]
            image_ext = visual_data.get("image_ext", "png")
            image_mime = visual_data.get("image_mime", "image/png")

        prefix = f"campaigns/{campaign_id}/versions/{version_id}"
        copy_gcs = await self._write_object(f"{prefix}/ad_copy.md", ad_copy_md_bytes, "text/markdown")
        img_gcs = await self._write_object(f"{prefix}/creative.{image_ext}", image_bytes, image_mime)

        copy_dl_token = self.mint_download_token(
            ad_copy_md_bytes,
            f"{campaign_id}_{version_id}_ad_copy.md",
            "text/markdown",
        )
        img_dl_token = self.mint_download_token(
            image_bytes,
            f"{campaign_id}_{version_id}_creative.{image_ext}",
            image_mime,
        )

        # Clean non-serializable raw bytes from visual_data copy
        clean_visual = {k: v for k, v in visual_data.items() if k != "raw_image_bytes"}

        version_record: dict[str, Any] = {
            "version_id": version_id,
            "version_number": version_number,
            "campaign_id": campaign_id,
            "campaign_name": camp["name"],
            "customer": "Acme Inc.",
            "parent_version_id": parent_version_id,
            "job_id": job_id,
            "author_action": author_action,
            "prompt_used": prompt_used,
            "diff_summary": diff_summary,
            "created_at": _utc_iso(),
            "models": {
                "ad_copy_model": ad_copy_data.get("model_used", "gemini-omni-flash-preview"),
                "visual_model": clean_visual.get("model_used", "gemini-3.1-flash-image-preview (Nano Banana)"),
            },
            "ad_copy": copy.deepcopy(ad_copy_data),
            "visual_creative": clean_visual,
            "reference_assets_used": reference_snapshot,
            "gcs": {
                "bucket": self.bucket_name,
                "version_prefix_uri": f"gs://{self.bucket_name}/{prefix}/",
                "bundle_gcs_uri": f"gs://{self.bucket_name}/{prefix}/bundle.json",
                "ad_copy_gcs_uri": copy_gcs["gcs_uri"],
                "creative_image_gcs_uri": img_gcs["gcs_uri"],
                "console_folder_url": (
                    f"https://console.cloud.google.com/storage/browser/"
                    f"{self.bucket_name}/{prefix}"
                ),
                "ad_copy_download_url": f"/download/{copy_dl_token}",
                "creative_image_download_url": f"/download/{img_dl_token}",
                "live_gcs_synced": copy_gcs["live_gcs_synced"],
                "content_sha256": hashlib.sha256(
                    json.dumps({"copy": ad_copy_data, "visual": clean_visual}, sort_keys=True).encode()
                ).hexdigest()[:16],
            },
        }

        bundle_bytes = json.dumps(version_record, indent=2).encode("utf-8")
        bundle_gcs = await self._write_object(
            f"{prefix}/bundle.json", bundle_bytes, "application/json"
        )
        bundle_dl_token = self.mint_download_token(
            bundle_bytes,
            f"{campaign_id}_{version_id}_bundle.json",
            "application/json",
        )
        version_record["gcs"]["bundle_download_url"] = f"/download/{bundle_dl_token}"
        version_record["gcs"]["bundle_sha256"] = bundle_gcs["sha256"]

        with self._lock:
            camp["versions"].append(version_record)
            camp["active_version_id"] = version_id
            camp["updated_at"] = _utc_iso()

        await self._sync_campaign_manifest(campaign_id)
        return copy.deepcopy(version_record)

    async def _sync_campaign_manifest(self, campaign_id: str) -> None:
        with self._lock:
            camp = self._campaigns.get(campaign_id)
            if not camp:
                return
            manifest = {
                "campaign_id": camp["campaign_id"],
                "name": camp["name"],
                "customer": camp["customer"],
                "product_name": camp["product_name"],
                "active_version_id": camp["active_version_id"],
                "updated_at": camp["updated_at"],
                "total_versions": len(camp["versions"]),
                "versions": [
                    {
                        "version_id": v["version_id"],
                        "version_number": v["version_number"],
                        "parent_version_id": v["parent_version_id"],
                        "author_action": v["author_action"],
                        "diff_summary": v["diff_summary"],
                        "created_at": v["created_at"],
                        "bundle_gcs_uri": v["gcs"]["bundle_gcs_uri"],
                        "content_sha256": v["gcs"]["content_sha256"],
                    }
                    for v in camp["versions"]
                ],
                "reference_assets": [
                    {
                        "asset_id": r["asset_id"],
                        "filename": r["filename"],
                        "asset_type": r["asset_type"],
                        "gcs_uri": r["gcs_uri"],
                        "uploaded_at": r["uploaded_at"],
                    }
                    for r in camp["reference_assets"]
                ],
            }
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
        await self._write_object(
            f"campaigns/{campaign_id}/manifest.json",
            manifest_bytes,
            "application/json",
        )

    def _compute_change_summary(
        self,
        prev_version: dict[str, Any] | None,
        new_copy: dict[str, Any],
        new_visual: dict[str, Any],
        author_action: str,
    ) -> str:
        if not prev_version:
            return f"Initial version v1 created ({author_action})"
        changed_fields: list[str] = []
        old_copy = prev_version.get("ad_copy") or {}
        old_vis = prev_version.get("visual_creative") or {}

        if old_copy.get("headline") != new_copy.get("headline"):
            changed_fields.append("headline")
        if old_copy.get("subheadline") != new_copy.get("subheadline"):
            changed_fields.append("subheadline")
        if old_copy.get("primary_copy") != new_copy.get("primary_copy"):
            changed_fields.append("primary copy")
        if old_copy.get("cta_text") != new_copy.get("cta_text"):
            changed_fields.append("CTA")
        if old_copy.get("channel_variants") != new_copy.get("channel_variants"):
            changed_fields.append("channel variants")
        if old_vis.get("visual_prompt") != new_visual.get("visual_prompt") or old_vis.get("aspect_ratio") != new_visual.get("aspect_ratio"):
            changed_fields.append("Nano Banana visual creative")

        if not changed_fields:
            return f"{author_action} (re-verified snapshot)"
        return f"{author_action} — updated {', '.join(changed_fields)}"

    # ------------------------------------------------------------------
    # Querying, Diffing & Restoring Content Versions
    # ------------------------------------------------------------------

    def get_campaign_sync(self, campaign_id: str) -> dict[str, Any] | None:
        with self._lock:
            camp = self._campaigns.get(campaign_id)
            return copy.deepcopy(camp) if camp else None

    def list_campaigns_sync(self) -> list[dict[str, Any]]:
        with self._lock:
            out = []
            for camp in self._campaigns.values():
                out.append({
                    "campaign_id": camp["campaign_id"],
                    "name": camp["name"],
                    "product_name": camp["product_name"],
                    "active_version_id": camp["active_version_id"],
                    "total_versions": len(camp["versions"]),
                    "reference_count": len(camp["reference_assets"]),
                    "updated_at": camp["updated_at"],
                })
            return out

    def list_versions_sync(self, campaign_id: str) -> list[dict[str, Any]]:
        with self._lock:
            camp = self._campaigns.get(campaign_id)
            if not camp:
                return []
            active_vid = camp.get("active_version_id")
            summaries = []
            for v in reversed(camp["versions"]):
                summaries.append({
                    "version_id": v["version_id"],
                    "version_number": v["version_number"],
                    "is_active": v["version_id"] == active_vid,
                    "parent_version_id": v["parent_version_id"],
                    "job_id": v["job_id"],
                    "author_action": v["author_action"],
                    "prompt_used": v["prompt_used"],
                    "diff_summary": v["diff_summary"],
                    "created_at": v["created_at"],
                    "headline": v["ad_copy"].get("headline", ""),
                    "cta_text": v["ad_copy"].get("cta_text", ""),
                    "aspect_ratio": v["visual_creative"].get("aspect_ratio", "1:1"),
                    "models": v["models"],
                    "gcs": v["gcs"],
                })
            return summaries

    def get_version_sync(
        self, campaign_id: str, version_id: str | None = None
    ) -> dict[str, Any] | None:
        with self._lock:
            camp = self._campaigns.get(campaign_id)
            if not camp or not camp["versions"]:
                return None
            target_id = version_id or camp.get("active_version_id")
            if not target_id:
                return copy.deepcopy(camp["versions"][-1])
            norm = str(target_id).strip().lower()
            if norm.isdigit():
                norm = f"v{norm}"
            for v in camp["versions"]:
                if v["version_id"].lower() == norm:
                    res = copy.deepcopy(v)
                    res["is_active"] = v["version_id"] == camp.get("active_version_id")
                    return res
            return None

    def set_active_version_sync(self, campaign_id: str, version_id: str) -> dict[str, Any] | None:
        with self._lock:
            camp = self._campaigns.get(campaign_id)
            if not camp:
                return None
            v = self.get_version_sync(campaign_id, version_id)
            if not v:
                return None
            camp["active_version_id"] = v["version_id"]
            camp["updated_at"] = _utc_iso()
            v["is_active"] = True
            return v

    def compare_versions_sync(
        self,
        campaign_id: str,
        base_version_id: str,
        target_version_id: str,
    ) -> dict[str, Any] | None:
        v_base = self.get_version_sync(campaign_id, base_version_id)
        v_target = self.get_version_sync(campaign_id, target_version_id)
        if not v_base or not v_target:
            return None

        fields_to_compare = [
            ("Headline", v_base["ad_copy"].get("headline", ""), v_target["ad_copy"].get("headline", "")),
            ("Subheadline", v_base["ad_copy"].get("subheadline", ""), v_target["ad_copy"].get("subheadline", "")),
            ("Primary Ad Copy", v_base["ad_copy"].get("primary_copy", ""), v_target["ad_copy"].get("primary_copy", "")),
            ("Call To Action", v_base["ad_copy"].get("cta_text", ""), v_target["ad_copy"].get("cta_text", "")),
            ("Target Audience", v_base["ad_copy"].get("target_audience", ""), v_target["ad_copy"].get("target_audience", "")),
            ("Brand Voice Score", str(v_base["ad_copy"].get("brand_voice_score", "")), str(v_target["ad_copy"].get("brand_voice_score", ""))),
            ("Nano Banana Visual Prompt", v_base["visual_creative"].get("visual_prompt", ""), v_target["visual_creative"].get("visual_prompt", "")),
            ("Aspect Ratio", v_base["visual_creative"].get("aspect_ratio", ""), v_target["visual_creative"].get("aspect_ratio", "")),
            ("Color Palette", ", ".join(v_base["visual_creative"].get("color_palette", [])), ", ".join(v_target["visual_creative"].get("color_palette", []))),
        ]

        # Also compare channel variants
        base_channels = v_base["ad_copy"].get("channel_variants") or {}
        target_channels = v_target["ad_copy"].get("channel_variants") or {}
        for ch_key in sorted(set(base_channels.keys()) | set(target_channels.keys())):
            fields_to_compare.append((
                f"Channel: {ch_key.replace('_', ' ').title()}",
                str(base_channels.get(ch_key, "")),
                str(target_channels.get(ch_key, "")),
            ))

        field_diffs = []
        changed_count = 0
        for label, before_val, after_val in fields_to_compare:
            changed = before_val != after_val
            if changed:
                changed_count += 1
            field_diffs.append({
                "field": label,
                "changed": changed,
                "base_value": before_val,
                "target_value": after_val,
            })

        return {
            "campaign_id": campaign_id,
            "base_version": {
                "version_id": v_base["version_id"],
                "created_at": v_base["created_at"],
                "author_action": v_base["author_action"],
                "gcs_uri": v_base["gcs"]["bundle_gcs_uri"],
                "image_data_uri": v_base["visual_creative"].get("image_data_uri", ""),
            },
            "target_version": {
                "version_id": v_target["version_id"],
                "created_at": v_target["created_at"],
                "author_action": v_target["author_action"],
                "gcs_uri": v_target["gcs"]["bundle_gcs_uri"],
                "image_data_uri": v_target["visual_creative"].get("image_data_uri", ""),
            },
            "changed_fields_count": changed_count,
            "total_fields_compared": len(field_diffs),
            "field_diffs": field_diffs,
        }
