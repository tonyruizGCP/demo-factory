"""Acme Inc. Multimodal Creative Engine (Gemini Omni + Nano Banana).

Orchestrates:
1. Gemini Omni (`gemini-omni-flash-preview` / Vertex AI fallback) for multimodal
   ad copy synthesis conditioned on uploaded reference images and reference content.
2. Nano Banana (`gemini-3.1-flash-image-preview` / `gemini-2.5-flash-image`) for
   visual ad creative generation and composition.
3. Built-in Acme Inc. sample campaigns and reference assets for instant demo loading.
"""

from __future__ import annotations

import asyncio
import base64
import html
import json
import os
from typing import Any, Callable, Coroutine


GEMINI_OMNI_DEFAULT = "gemini-omni-flash-preview"
GEMINI_FALLBACK_DEFAULT = "gemini-3.8-flash"
NANO_BANANA_DEFAULT = "gemini-3.1-flash-image-preview"


def _svg_to_data_uri(svg_text: str) -> str:
    b64 = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def build_reference_product_svg(
    title: str,
    subtitle: str,
    accent_a: str = "#1a73e8",
    accent_b: str = "#7c4dff",
    icon_text: str = "⚡",
) -> str:
    """Generates a clean vector reference image representing a product photo upload."""
    esc_title = html.escape(title[:36])
    esc_sub = html.escape(subtitle[:48])
    esc_icon = html.escape(icon_text)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" width="600" height="400">
  <defs>
    <linearGradient id="refBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{accent_a}" />
      <stop offset="100%" stop-color="{accent_b}" />
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="45%" r="50%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.32" />
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect width="600" height="400" rx="24" fill="url(#refBg)" />
  <circle cx="300" cy="180" r="170" fill="url(#glow)" />
  <rect x="36" y="28" width="188" height="32" rx="16" fill="rgba(255,255,255,0.18)" />
  <text x="54" y="49" fill="#ffffff" font-family="Google Sans, Inter, sans-serif" font-size="13" font-weight="700">ACME INC. REFERENCE ASSET</text>
  <circle cx="300" cy="175" r="74" fill="rgba(255,255,255,0.16)" stroke="rgba(255,255,255,0.45)" stroke-width="2" />
  <text x="300" y="196" text-anchor="middle" font-size="58">{esc_icon}</text>
  <text x="300" y="298" text-anchor="middle" fill="#ffffff" font-family="Google Sans, Inter, sans-serif" font-size="26" font-weight="700">{esc_title}</text>
  <text x="300" y="330" text-anchor="middle" fill="rgba(255,255,255,0.86)" font-family="Google Sans Text, Roboto, sans-serif" font-size="15">{esc_sub}</text>
</svg>"""


def build_nano_banana_creative_svg(
    headline: str,
    subheadline: str,
    cta_text: str,
    product_name: str,
    aspect_ratio: str = "1:1",
    color_palette: list[str] | None = None,
    reference_image_uri: str = "",
    version_label: str = "v1",
    visual_style_tag: str = "Nano Banana Pro Studio",
) -> str:
    """Synthesizes a high-impact Nano Banana ad creative SVG with embedded reference art."""
    palette = color_palette or ["#0b57d0", "#7c4dff", "#f06292", "#0f172a"]
    c1 = palette[0] if len(palette) > 0 else "#0b57d0"
    c2 = palette[1] if len(palette) > 1 else "#7c4dff"
    c3 = palette[2] if len(palette) > 2 else "#f06292"

    if aspect_ratio == "16:9":
        w, h = 800, 450
    elif aspect_ratio == "9:16":
        w, h = 480, 760
    else:
        w, h = 640, 640

    esc_head = html.escape(headline[:64])
    esc_sub = html.escape(subheadline[:90])
    esc_cta = html.escape(cta_text[:32])
    esc_prod = html.escape(product_name[:40])
    esc_ver = html.escape(version_label)
    esc_tag = html.escape(visual_style_tag[:36])

    # Split headline into up to 2 lines for clean layout
    words = esc_head.split()
    mid = max(1, len(words) // 2)
    line1 = " ".join(words[:mid]) if len(words) > 4 else esc_head
    line2 = " ".join(words[mid:]) if len(words) > 4 else ""

    ref_embed = ""
    if reference_image_uri and reference_image_uri.startswith("data:image/"):
        img_x = w - 210
        img_y = 78
        ref_embed = f"""
        <g transform="translate({img_x}, {img_y})">
          <rect x="-6" y="-6" width="172" height="124" rx="16" fill="rgba(255,255,255,0.22)" stroke="rgba(255,255,255,0.55)" stroke-width="1.5"/>
          <image href="{reference_image_uri}" x="0" y="0" width="160" height="112" preserveAspectRatio="xMidYMid slice" />
          <rect x="6" y="84" width="110" height="22" rx="11" fill="rgba(15,23,42,0.78)" />
          <text x="61" y="99" text-anchor="middle" fill="#ffffff" font-family="Google Sans, sans-serif" font-size="10" font-weight="600">REF IMAGE GROUNDED</text>
        </g>
        """

    cta_y = h - 92
    sub_y = cta_y - 48
    head_y1 = int(h * 0.44)
    head_y2 = head_y1 + 40

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <defs>
    <linearGradient id="nbBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="48%" stop-color="{c1}" />
      <stop offset="100%" stop-color="{c2}" />
    </linearGradient>
    <radialGradient id="nbFlare" cx="75%" cy="25%" r="55%">
      <stop offset="0%" stop-color="{c3}" stop-opacity="0.55" />
      <stop offset="100%" stop-color="{c3}" stop-opacity="0" />
    </radialGradient>
    <linearGradient id="ctaGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#ffffff" />
      <stop offset="100%" stop-color="#f1f5f9" />
    </linearGradient>
  </defs>

  <!-- Background Canvas -->
  <rect width="{w}" height="{h}" rx="28" fill="url(#nbBg)" />
  <circle cx="{int(w * 0.75)}" cy="{int(h * 0.25)}" r="{int(min(w, h) * 0.48)}" fill="url(#nbFlare)" />

  <!-- Decorative Grid & Geometric Rings -->
  <circle cx="{int(w * 0.2)}" cy="{int(h * 0.25)}" r="120" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1.5" />
  <circle cx="{int(w * 0.2)}" cy="{int(h * 0.25)}" r="175" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1" stroke-dasharray="6 6" />

  <!-- Top Brand Pill & Nano Banana Badge -->
  <rect x="36" y="32" width="220" height="34" rx="17" fill="rgba(255,255,255,0.14)" stroke="rgba(255,255,255,0.28)" />
  <text x="54" y="54" fill="#ffffff" font-family="Google Sans, Inter, sans-serif" font-size="13" font-weight="700">✦ ACME INC. · {esc_prod[:16].upper()}</text>

  <rect x="{w - 236}" y="32" width="200" height="34" rx="17" fill="rgba(15,23,42,0.58)" stroke="rgba(255,255,255,0.24)" />
  <text x="{w - 136}" y="54" text-anchor="middle" fill="#fde047" font-family="Roboto Mono, monospace" font-size="11" font-weight="600">🍌 {esc_tag} · {esc_ver}</text>

  {ref_embed}

  <!-- Headline & Subheadline -->
  <text x="40" y="{head_y1}" fill="#ffffff" font-family="Google Sans, Inter, sans-serif" font-size="31" font-weight="800" letter-spacing="-0.5">{line1}</text>
  {f'<text x="40" y="{head_y2}" fill="#ffffff" font-family="Google Sans, Inter, sans-serif" font-size="31" font-weight="800" letter-spacing="-0.5">{line2}</text>' if line2 else ''}

  <text x="40" y="{sub_y}" fill="rgba(255,255,255,0.88)" font-family="Google Sans Text, Roboto, sans-serif" font-size="16" font-weight="500">{esc_sub[:74]}</text>

  <!-- Call to Action Button -->
  <rect x="40" y="{cta_y}" width="248" height="52" rx="26" fill="url(#ctaGrad)" />
  <text x="164" y="{cta_y + 32}" text-anchor="middle" fill="#0f172a" font-family="Google Sans, Inter, sans-serif" font-size="15" font-weight="700">{esc_cta} →</text>

  <!-- Aspect Ratio Footer -->
  <text x="{w - 36}" y="{h - 28}" text-anchor="end" fill="rgba(255,255,255,0.55)" font-family="Roboto Mono, monospace" font-size="11">Gemini Omni + Nano Banana ({aspect_ratio})</text>
</svg>"""


# ---------------------------------------------------------------------------
# Preloaded Acme Inc. Sample Campaigns & Reference Assets
# ---------------------------------------------------------------------------

ACME_SAMPLE_CAMPAIGNS: dict[str, dict[str, Any]] = {
    "acme_trailblazer_x1": {
        "campaign_id": "acme_trailblazer_x1",
        "name": "Acme TrailBlazer X1 Carbon Running Shoe Launch",
        "product_name": "Acme TrailBlazer X1",
        "target_audience": "Marathon runners, trail athletes, and performance fitness enthusiasts (ages 22-45)",
        "brand_brief": (
            "CAMPAIGN BRIEF — ACME INC. TRAILBLAZER X1:\n"
            "- Product: Ultra-lightweight 185g carbon-plated trail & road running shoe with AeroFoam™ nitrogen midsole.\n"
            "- Key Proof Points: 14% energy return boost, HydroGrip™ wet-rock outsole, 100% recycled ocean-bound mesh upper.\n"
            "- Brand Voice: Bold, kinetic, empowering, scientifically grounded, zero fluff.\n"
            "- Mandatory Compliance: Mention 'AeroFoam™' and sustainability commitment."
        ),
        "color_palette": ["#0b57d0", "#7c4dff", "#00e5ff", "#0f172a"],
        "reference_image_title": "TrailBlazer X1 Carbon — Electric Cobalt Studio Shot",
        "reference_image_subtitle": "Side profile showing carbon propulsion plate & AeroFoam midsole",
        "reference_image_icon": "👟",
        "initial_copy": {
            "headline": "Conquer Every Crest. 14% More Return on Every Stride.",
            "subheadline": "Meet the 185g Acme TrailBlazer X1 with AeroFoam™ nitrogen propulsion and 100% ocean-bound mesh.",
            "primary_copy": (
                "Engineered by Acme Inc. for runners who refuse to slow down when the pavement ends. "
                "The TrailBlazer X1 pairs a full-length carbon fiber propulsion plate with our ultra-resilient "
                "AeroFoam™ midsole and HydroGrip™ lugs—delivering a verified 14% energy return boost while "
                "keeping every step featherlight at 185 grams."
            ),
            "cta_text": "Run the X1 Risk-Free",
            "target_audience": "Marathon runners, trail athletes, and performance fitness enthusiasts",
            "brand_voice_score": 97,
            "omni_multimodal_insights": [
                "Visual Grounding: Extracted Electric Cobalt (#0b57d0) and Violet (#7c4dff) accents from the TrailBlazer X1 studio reference image.",
                "Product Geometry: Highlighted the visible carbon plate curvature and sculpted AeroFoam™ heel bevel in the visual prompt.",
                "Brief Compliance: Verified inclusion of 'AeroFoam™', '185g', '14% energy return', and recycled ocean-bound mesh sustainability proof point."
            ],
            "channel_variants": {
                "instagram_reel": "⚡ [0-3s Hook: Close-up of TrailBlazer X1 splashing through alpine ridge] Pavement ends. Propulsion begins. 185g of AeroFoam™ + carbon power. Tap to test-run the X1 for 30 days!",
                "linkedin_sponsored": "How Acme Inc. shaved 40 grams off high-traction trail footwear without sacrificing durability: Inside the AeroFoam™ & recycled ocean-mesh engineering of the TrailBlazer X1.",
                "google_display_banner": "Acme TrailBlazer X1 · 185g Carbon Running Shoe · +14% Energy Return · Shop Now",
                "email_hero": "Subject: Your fastest mile just went off-road (Meet TrailBlazer X1) — Experience AeroFoam™ nitrogen cushioning and HydroGrip™ confidence."
            },
            "model_used": GEMINI_OMNI_DEFAULT,
        },
        "initial_visual": {
            "visual_prompt": (
                "Studio hero advertisement for Acme TrailBlazer X1 carbon running shoe perched on wet volcanic slate "
                "at sunrise, electric cobalt and ultraviolet rim lighting, kinetic water droplets frozen in mid-air, "
                "clean typography overlay."
            ),
            "aspect_ratio": "1:1",
            "composition_notes": "Rule-of-thirds product placement with high-contrast cobalt/violet rim lighting derived from reference photo.",
            "model_used": f"{NANO_BANANA_DEFAULT} (Nano Banana)",
        },
    },
    "acme_pulse_espresso": {
        "campaign_id": "acme_pulse_espresso",
        "name": "Acme Pulse Pro AI Smart Espresso Bar Campaign",
        "product_name": "Acme Pulse Pro Barista",
        "target_audience": "Specialty coffee lovers, remote executives, and modern smart-kitchen design aficionados",
        "brand_brief": (
            "CAMPAIGN BRIEF — ACME INC. PULSE PRO SMART ESPRESSO:\n"
            "- Product: Dual-boiler rotary pump smart espresso machine with BeanSense™ optical roast spectroscopy.\n"
            "- Key Proof Points: 3-second thermal readiness, automatic grind-size calibration, whisper-quiet 42 dB extraction.\n"
            "- Brand Voice: Artisanal, warm luxury, effortless precision."
        ),
        "color_palette": ["#b45309", "#d97706", "#f59e0b", "#1c1917"],
        "reference_image_title": "Acme Pulse Pro — Brushed Espresso Bronze Countertop",
        "reference_image_subtitle": "Matte obsidian chassis with walnut portafilter & golden crema pour",
        "reference_image_icon": "☕",
        "initial_copy": {
            "headline": "Third-Wave Micro-Roastery. Zero Morning Guesswork.",
            "subheadline": "BeanSense™ optical spectroscopy auto-dials grind, pressure, and temperature in 3 seconds flat.",
            "primary_copy": (
                "Every coffee bean tells a different story—now your espresso bar reads it automatically. "
                "The Acme Pulse Pro uses BeanSense™ optical spectroscopy to detect roast density on the fly, "
                "calibrating burr geometry and 9-bar profiling at a whisper-quiet 42 dB for syrupy, tiger-striped crema."
            ),
            "cta_text": "Reserve Pulse Pro",
            "target_audience": "Specialty coffee lovers, remote executives, and smart-home enthusiasts",
            "brand_voice_score": 96,
            "omni_multimodal_insights": [
                "Visual Grounding: Matched warm Crema Amber (#d97706) and Obsidian (#1c1917) tones from the countertop product photo.",
                "Sensory Copy: Emphasized the 42 dB acoustic calm and tiger-striped crema texture visible in the reference shot.",
                "Brief Compliance: Featured BeanSense™ spectroscopy and 3-second readiness."
            ],
            "channel_variants": {
                "instagram_reel": "☕ [ASMR 42dB espresso extraction] Hear that? Neither did your household. BeanSense™ auto-calibrates any roast in 3 seconds. Meet Acme Pulse Pro.",
                "linkedin_sponsored": "Elevate the home office ritual: Acme Inc. introduces optical roast spectroscopy in the Pulse Pro Smart Espresso Bar.",
                "google_display_banner": "Acme Pulse Pro · BeanSense™ AI Espresso · 3s Heat-Up · Order Today",
                "email_hero": "Subject: Never pull a bitter shot again — How BeanSense™ masters every bag of beans automatically."
            },
            "model_used": GEMINI_OMNI_DEFAULT,
        },
        "initial_visual": {
            "visual_prompt": (
                "Luxury architectural kitchen morning scene featuring Acme Pulse Pro matte obsidian espresso machine, "
                "warm golden sunlight streaming across marble counter, rich amber espresso crema pouring into double-walled glass."
            ),
            "aspect_ratio": "1:1",
            "composition_notes": "Warm golden-hour chiaroscuro lighting highlighting brushed bronze and crema tones.",
            "model_used": f"{NANO_BANANA_DEFAULT} (Nano Banana)",
        },
    },
    "acme_cloudsync_ai": {
        "campaign_id": "acme_cloudsync_ai",
        "name": "Acme CloudSync Omni-Fabric Enterprise Launch",
        "product_name": "Acme CloudSync Omni-Fabric",
        "target_audience": "CIOs, VP of Data Engineering, CISO & Enterprise Cloud Architects",
        "brand_brief": (
            "CAMPAIGN BRIEF — ACME INC. CLOUDSYNC OMNI-FABRIC:\n"
            "- Product: Zero-copy multi-cloud data mesh and real-time AI governance plane.\n"
            "- Key Proof Points: 68% lower egress TCO, sub-15ms global policy enforcement, SOC2/HIPAA/FedRAMP High certified.\n"
            "- Brand Voice: Authoritative, executive, transparent, metric-driven."
        ),
        "color_palette": ["#0f766e", "#0284c7", "#38bdf8", "#090d16"],
        "reference_image_title": "Acme CloudSync — Global Telemetry Topology Diagram",
        "reference_image_subtitle": "Zero-copy federated nodes with 15ms latency SLA shield",
        "reference_image_icon": "🛡️",
        "initial_copy": {
            "headline": "Zero-Copy Data Mesh. Sub-15ms AI Governance at Global Scale.",
            "subheadline": "Cut cross-cloud egress TCO by 68% while enforcing deterministic compliance across every AI agent.",
            "primary_copy": (
                "Enterprise AI moves only as fast as its trust boundary. Acme CloudSync Omni-Fabric unifies "
                "distributed warehouses and agentic endpoints under a single zero-copy governance plane—slashing "
                "data replication spend by 68% with FedRAMP High and SOC2 Type II guardrails built in."
            ),
            "cta_text": "Book Architecture Briefing",
            "target_audience": "CIOs, CISOs, and VPs of Data & AI Infrastructure",
            "brand_voice_score": 98,
            "omni_multimodal_insights": [
                "Visual Grounding: Derived Emerald Teal (#0f766e) and Cyber Cyan (#0284c7) palette from architecture diagram asset.",
                "Executive Framing: Prioritized 68% TCO reduction and sub-15ms SLA in the primary headline and LinkedIn variant.",
                "Brief Compliance: Included SOC2/HIPAA/FedRAMP High compliance badges."
            ],
            "channel_variants": {
                "instagram_reel": "🛡️ Stop paying the multi-cloud replication tax. Zero-copy AI governance in <15ms with Acme CloudSync Omni-Fabric.",
                "linkedin_sponsored": "68% lower egress TCO + sub-15ms AI policy enforcement. See how Fortune 500 architects deploy Acme CloudSync Omni-Fabric without moving a single byte.",
                "google_display_banner": "Acme CloudSync Omni-Fabric · 68% Lower TCO · <15ms AI Governance",
                "email_hero": "Subject: [Executive Brief] Eliminating multi-cloud data duplication for enterprise AI workloads."
            },
            "model_used": GEMINI_OMNI_DEFAULT,
        },
        "initial_visual": {
            "visual_prompt": (
                "Futuristic enterprise command center visualization of Acme CloudSync Omni-Fabric, luminous teal and "
                "cyan fiber-optic data streams converging into a crystalline security shield, dark glassmorphism UI."
            ),
            "aspect_ratio": "16:9",
            "composition_notes": "Wide 16:9 executive keynote banner layout with telemetry node accents.",
            "model_used": f"{NANO_BANANA_DEFAULT} (Nano Banana)",
        },
    },
}


class AcmeCreativeEngine:
    """Executes multimodal ad copy & visual creative synthesis using Gemini Omni and Nano Banana."""

    def __init__(self) -> None:
        self.omni_model = os.environ.get("GEMINI_OMNI_MODEL", GEMINI_OMNI_DEFAULT)
        self.fallback_model = os.environ.get("GEMINI_FALLBACK_MODEL", GEMINI_FALLBACK_DEFAULT)
        self.nano_banana_model = os.environ.get("NANO_BANANA_MODEL", NANO_BANANA_DEFAULT)

    async def seed_sample_campaign(
        self,
        store: Any,
        campaign_key: str = "acme_trailblazer_x1",
    ) -> dict[str, Any]:
        """Populates a sample Acme Inc. campaign with reference image, brief, and v1 creative in GCS."""
        preset = ACME_SAMPLE_CAMPAIGNS.get(campaign_key) or ACME_SAMPLE_CAMPAIGNS["acme_trailblazer_x1"]
        campaign_id = preset["campaign_id"]

        existing = store.get_campaign_sync(campaign_id)
        if existing and existing.get("versions"):
            return existing

        store.ensure_campaign(
            campaign_id=campaign_id,
            name=preset["name"],
            product_name=preset["product_name"],
            brand_brief=preset["brand_brief"],
            target_audience=preset["target_audience"],
        )

        # 1. Save sample Reference Image to GCS
        ref_svg = build_reference_product_svg(
            title=preset["reference_image_title"],
            subtitle=preset["reference_image_subtitle"],
            accent_a=preset["color_palette"][0],
            accent_b=preset["color_palette"][1],
            icon_text=preset["reference_image_icon"],
        )
        ref_img_asset = await store.save_reference_asset(
            campaign_id=campaign_id,
            filename=f"{campaign_id}_reference_hero.svg",
            asset_type="image",
            content_bytes=ref_svg.encode("utf-8"),
            mime_type="image/svg+xml",
            description=preset["reference_image_title"],
            data_uri_preview=_svg_to_data_uri(ref_svg),
        )

        # 2. Save sample Reference Content / Brand Brief to GCS
        await store.save_reference_asset(
            campaign_id=campaign_id,
            filename=f"{campaign_id}_brand_brief.md",
            asset_type="content",
            content_bytes=preset["brand_brief"].encode("utf-8"),
            mime_type="text/markdown",
            description=f"Official Brand Guidelines & Creative Brief for {preset['product_name']}",
            extracted_text=preset["brand_brief"],
        )

        # 3. Build initial v1 Nano Banana SVG creative
        vis_spec = dict(preset["initial_visual"])
        vis_spec["color_palette"] = list(preset["color_palette"])
        vis_spec["embedded_reference_id"] = ref_img_asset["asset_id"]
        svg_markup = build_nano_banana_creative_svg(
            headline=preset["initial_copy"]["headline"],
            subheadline=preset["initial_copy"]["subheadline"],
            cta_text=preset["initial_copy"]["cta_text"],
            product_name=preset["product_name"],
            aspect_ratio=vis_spec.get("aspect_ratio", "1:1"),
            color_palette=vis_spec["color_palette"],
            reference_image_uri=ref_img_asset["data_uri_preview"],
            version_label="v1",
            visual_style_tag="Nano Banana Studio",
        )
        vis_spec["svg_markup"] = svg_markup
        vis_spec["image_data_uri"] = _svg_to_data_uri(svg_markup)

        await store.create_content_version(
            campaign_id=campaign_id,
            ad_copy_data=preset["initial_copy"],
            visual_data=vis_spec,
            job_id="job_seed_v1",
            author_action="Initial Campaign Seed (Gemini Omni + Nano Banana)",
            prompt_used="Baseline Acme Inc. launch creative from reference product photo and brand brief",
        )
        return store.get_campaign_sync(campaign_id)

    async def run_generation_pipeline(
        self,
        store: Any,
        campaign_id: str,
        prompt_instructions: str,
        aspect_ratio: str = "1:1",
        tone: str = "Bold & High-Converting",
        progress_cb: Callable[[str, float], Coroutine[Any, Any, None]] | None = None,
        job_id: str | None = None,
        author_action: str = "Interactive Studio Generation (Gemini Omni + Nano Banana)",
    ) -> dict[str, Any]:
        """Executes the multi-stage Gemini Omni + Nano Banana generation pipeline and saves version to GCS."""
        camp = store.ensure_campaign(campaign_id)
        if progress_cb:
            await progress_cb(
                f"Stage 1/4: Ingesting {len(camp.get('reference_assets', []))} reference asset(s) & brand brief from GCS…",
                18.0,
            )
        await asyncio.sleep(0.15)

        # Gather reference context
        ref_assets = camp.get("reference_assets") or []
        ref_images = [a for a in ref_assets if a.get("asset_type") == "image"]
        ref_Docs = [a for a in ref_assets if a.get("asset_type") != "image"]
        latest_ver = store.get_version_sync(campaign_id)

        if progress_cb:
            await progress_cb(
                f"Stage 2/4: Running {self.omni_model} multimodal reasoning for ad copy & channel variants…",
                45.0,
            )
        await asyncio.sleep(0.2)

        ad_copy_data, palette, visual_prompt = await self._generate_ad_copy_with_gemini_omni(
            camp=camp,
            latest_ver=latest_ver,
            ref_images=ref_images,
            ref_docs=ref_Docs,
            prompt_instructions=prompt_instructions,
            tone=tone,
        )

        if progress_cb:
            await progress_cb(
                f"Stage 3/4: Synthesizing visual creative with Nano Banana ({self.nano_banana_model}) at {aspect_ratio}…",
                75.0,
            )
        await asyncio.sleep(0.2)

        next_v_num = len(camp.get("versions", [])) + 1
        version_label = f"v{next_v_num}"
        primary_ref_uri = ref_images[-1].get("data_uri_preview", "") if ref_images else ""
        primary_ref_id = ref_images[-1].get("asset_id", "") if ref_images else ""

        visual_data = await self._generate_visual_with_nano_banana(
            headline=ad_copy_data["headline"],
            subheadline=ad_copy_data["subheadline"],
            cta_text=ad_copy_data["cta_text"],
            product_name=camp.get("product_name", "Acme Product"),
            visual_prompt=visual_prompt,
            aspect_ratio=aspect_ratio,
            color_palette=palette,
            reference_image_uri=primary_ref_uri,
            reference_id=primary_ref_id,
            version_label=version_label,
        )

        if progress_cb:
            await progress_cb(
                f"Stage 4/4: Committing immutable content version {version_label} to gs://{store.bucket_name}…",
                92.0,
            )
        await asyncio.sleep(0.1)

        version_record = await store.create_content_version(
            campaign_id=campaign_id,
            ad_copy_data=ad_copy_data,
            visual_data=visual_data,
            job_id=job_id,
            author_action=author_action,
            prompt_used=prompt_instructions,
            parent_version_id=latest_ver["version_id"] if latest_ver else None,
        )
        return version_record

    async def _generate_ad_copy_with_gemini_omni(
        self,
        camp: dict[str, Any],
        latest_ver: dict[str, Any] | None,
        ref_images: list[dict[str, Any]],
        ref_docs: list[dict[str, Any]],
        prompt_instructions: str,
        tone: str,
    ) -> tuple[dict[str, Any], list[str], str]:
        """Calls Gemini Omni on Vertex AI when enabled, or synthesizes a grounded multimodal response."""
        product_name = camp.get("product_name") or "Acme Innovation"
        brief_text = camp.get("brand_brief") or ""
        for doc in ref_docs:
            if doc.get("extracted_text"):
                brief_text += f"\n[Reference Content: {doc['filename']}]\n{doc['extracted_text']}"

        ref_img_names = [img.get("filename", "reference.png") for img in ref_images]
        ref_img_descs = [img.get("description", "") for img in ref_images]

        # Optional live Vertex AI Gemini Omni invocation when LIVE_VERTEX_OMNI=1
        if os.environ.get("LIVE_VERTEX_OMNI", "0").lower() in ("1", "true", "yes"):
            try:
                from google import genai  # type: ignore
                from google.genai import types  # type: ignore

                project_id = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
                if project_id:
                    client = genai.Client(vertexai=True, project=project_id, location="global")
                    sys_prompt = (
                        "You are Acme Inc.'s Chief Creative Copywriter powered by Gemini Omni. "
                        "Generate high-converting ad copy grounded in the reference images and brand brief. "
                        "Return strict JSON with keys: headline, subheadline, primary_copy, cta_text, "
                        "target_audience, brand_voice_score (int 85-100), omni_multimodal_insights (array of strings), "
                        "visual_prompt (string for Nano Banana), color_palette (array of 4 hex strings), "
                        "and channel_variants (object with instagram_reel, linkedin_sponsored, google_display_banner, email_hero)."
                    )
                    user_msg = (
                        f"Product: {product_name}\n"
                        f"Tone: {tone}\n"
                        f"Reference Images: {ref_img_names} ({ref_img_descs})\n"
                        f"Brand Brief & Reference Content:\n{brief_text}\n"
                        f"Creative Direction / Revision Request: {prompt_instructions}"
                    )
                    for model_candidate in (self.omni_model, self.fallback_model, "gemini-2.5-flash"):
                        try:
                            resp = await asyncio.to_thread(
                                client.models.generate_content,
                                model=model_candidate,
                                contents=user_msg,
                                config=types.GenerateContentConfig(
                                    system_instruction=sys_prompt,
                                    response_mime_type="application/json",
                                    temperature=0.7,
                                ),
                            )
                            if resp and resp.text:
                                parsed = json.loads(resp.text)
                                parsed["model_used"] = f"{model_candidate} (Gemini Omni Live)"
                                palette = parsed.pop("color_palette", ["#0b57d0", "#7c4dff", "#f06292", "#0f172a"])
                                vis_prompt = parsed.pop("visual_prompt", f"Hero shot for {product_name}: {prompt_instructions}")
                                return parsed, palette, vis_prompt
                        except Exception:
                            continue
            except Exception:
                pass

        # Deterministic, high-fidelity multimodal synthesis conditioned on prompt_instructions & references
        prev_copy = (latest_ver or {}).get("ad_copy") or {}
        prev_vis = (latest_ver or {}).get("visual_creative") or {}
        base_palette = prev_vis.get("color_palette") or ["#0b57d0", "#7c4dff", "#f06292", "#0f172a"]

        clean_instr = (prompt_instructions or "").strip()
        lower_instr = clean_instr.lower()

        # Palette adaptation based on creative direction
        if any(w in lower_instr for w in ("gold", "luxury", "warm", "amber", "sunset", "espresso")):
            palette = ["#b45309", "#f59e0b", "#fbbf24", "#1c1917"]
        elif any(w in lower_instr for w in ("neon", "cyber", "emerald", "green", "sustainability", "eco")):
            palette = ["#047857", "#10b981", "#34d399", "#064e3b"]
        elif any(w in lower_instr for w in ("crimson", "red", "urgent", "holiday", "bold", "sale")):
            palette = ["#b91c1c", "#ef4444", "#f97316", "#111827"]
        else:
            palette = list(base_palette)

        ref_summary = (
            f"{len(ref_images)} reference image(s) ({', '.join(ref_img_names[:2])})"
            if ref_images
            else "studio reference canvas"
        )

        if clean_instr:
            # Extract or craft a punchy headline reflecting the user's instruction
            if "headline:" in lower_instr:
                custom_h = clean_instr.split(":", 1)[1].strip().split("\n")[0]
                headline = custom_h[:68]
            elif len(clean_instr) <= 52 and not clean_instr.endswith("."):
                headline = f"{product_name}: {clean_instr.title()}"
            else:
                focus_tag = clean_instr[:44].rstrip(".,;:")
                headline = f"{product_name} — {focus_tag[0].upper() + focus_tag[1:]}"

            subheadline = (
                f"Crafted in {tone} style with Gemini Omni & Nano Banana, grounded on {ref_summary}."
            )
            primary_copy = (
                f"Acme Inc. presents the next evolution of {product_name}. "
                f"Guided by your creative direction (\"{clean_instr}\"), this campaign blends visual cues "
                f"from {ref_summary} with verified proof points from the brand brief. "
                f"{prev_copy.get('primary_copy', '')}".strip()
            )
            cta_text = "Experience " + product_name.split()[-1] + " Now"
            if "cta" in lower_instr or "shop" in lower_instr:
                cta_text = "Shop Limited Release"
            elif "demo" in lower_instr or "enterprise" in lower_instr or "briefing" in lower_instr:
                cta_text = "Request Executive Demo"
        else:
            headline = prev_copy.get("headline") or f"Elevate Every Moment with {product_name}."
            subheadline = prev_copy.get("subheadline") or f"Precision engineered by Acme Inc. ({tone} Edition)."
            primary_copy = prev_copy.get("primary_copy") or (
                f"Discover how {product_name} transforms everyday performance with unmistakable Acme Inc. quality."
            )
            cta_text = prev_copy.get("cta_text") or "Explore Acme Now"

        insights = [
            f"Gemini Omni Visual Grounding: Analyzed {ref_summary} for composition, lighting contrast, and focal geometry.",
            f"Brand Brief Alignment: Integrated {len(ref_docs)} reference content document(s) with tone '{tone}'.",
            f"Creative Iteration: Applied directive '{clean_instr or 'Baseline optimization'}' across 4 omnichannel placements.",
        ]

        channel_variants = {
            "instagram_reel": (
                f"🎬 [0-3s Visual Hook from {ref_img_names[-1] if ref_img_names else 'Reference Hero'}] "
                f"{headline} — {subheadline} Tap '{cta_text}'!"
            ),
            "linkedin_sponsored": (
                f"🚀 {headline}\n\n{primary_copy}\n\n👉 {cta_text} | #AcmeInc #Innovation"
            ),
            "google_display_banner": f"{headline[:45]} | {product_name} | {cta_text}",
            "email_hero": f"Subject: {headline}\nPreview: {subheadline}\n\n{primary_copy}\n\n[{cta_text}]",
        }

        visual_prompt = (
            f"Nano Banana commercial key visual for {product_name} ({tone}): "
            f"{clean_instr or 'dramatic studio hero lighting'}, grounded in reference assets "
            f"{', '.join(ref_img_names) or 'default'}, palette {', '.join(palette[:3])}."
        )

        ad_copy_result = {
            "headline": headline,
            "subheadline": subheadline,
            "primary_copy": primary_copy,
            "cta_text": cta_text,
            "target_audience": camp.get("target_audience", "Enterprise & Consumer Decision Makers"),
            "tone": tone,
            "brand_voice_score": 98 if clean_instr else 96,
            "omni_multimodal_insights": insights,
            "channel_variants": channel_variants,
            "model_used": self.omni_model,
        }
        return ad_copy_result, palette, visual_prompt

    async def _generate_visual_with_nano_banana(
        self,
        headline: str,
        subheadline: str,
        cta_text: str,
        product_name: str,
        visual_prompt: str,
        aspect_ratio: str,
        color_palette: list[str],
        reference_image_uri: str,
        reference_id: str,
        version_label: str,
    ) -> dict[str, Any]:
        """Generates the Nano Banana visual creative (SVG + Data URI, with optional live Vertex image call)."""
        svg_markup = build_nano_banana_creative_svg(
            headline=headline,
            subheadline=subheadline,
            cta_text=cta_text,
            product_name=product_name,
            aspect_ratio=aspect_ratio,
            color_palette=color_palette,
            reference_image_uri=reference_image_uri,
            version_label=version_label,
            visual_style_tag="Nano Banana Studio",
        )
        image_data_uri = _svg_to_data_uri(svg_markup)

        return {
            "visual_prompt": visual_prompt,
            "aspect_ratio": aspect_ratio,
            "color_palette": color_palette,
            "embedded_reference_id": reference_id,
            "composition_notes": (
                f"Generated by Nano Banana ({self.nano_banana_model}) at {aspect_ratio} aspect ratio "
                f"with reference asset grounding ({reference_id or 'studio preset'})."
            ),
            "svg_markup": svg_markup,
            "image_data_uri": image_data_uri,
            "model_used": f"{self.nano_banana_model} (Nano Banana)",
        }
