"""Gemini 4 Hydrogen multimodal agent and Demo Factory entrypoint."""

import json
import os
import time
from typing import Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from app.config import (
    CLIP_PATH,
    FORCE_SIMULATION,
    GCP_LOCATION,
    GCP_PROJECT,
    KEYFRAMES,
    MODEL_ID,
)
from app.simulation import get_simulated_response


class ActionSegment(BaseModel):
    start_time: str = Field(description="Start timestamp in MM:SS format")
    end_time: str = Field(description="End timestamp in MM:SS format")
    action_label: str = Field(description="Short verb-object assembly action")
    components_or_tools: list[str] = Field(description="Bicycle parts or tools involved")
    worker_posture: str = Field(description="Standing, crouching, bending, walking, etc.")
    visual_evidence: str = Field(description="Brief description of what is observed")


class AssemblyTimeline(BaseModel):
    scene_summary: str
    total_segments: int
    segments: list[ActionSegment]


def _build_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client(vertexai=True, project=GCP_PROJECT, location=GCP_LOCATION)


def _extract_thoughts_and_text(response: Any) -> tuple[str, str]:
    thoughts: list[str] = []
    texts: list[str] = []
    for cand in getattr(response, "candidates", []) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", []) or []:
            if getattr(part, "thought", False) and getattr(part, "text", None):
                thoughts.append(part.text)
            elif getattr(part, "text", None):
                texts.append(part.text)
    return "\n".join(thoughts).strip(), ("\n".join(texts).strip() or (response.text or ""))


def run_multimodal_analysis(
    mode: str,
    custom_prompt: str = "",
    thinking_level: str = "MEDIUM",
) -> dict[str, Any]:
    """Run Gemini 4 Hydrogen multimodal analysis with offline simulation fallback."""
    valid_levels = {"LOW", "MEDIUM", "HIGH", "XHIGH"}
    level = thinking_level.upper() if thinking_level.upper() in valid_levels else "MEDIUM"

    if FORCE_SIMULATION:
        return get_simulated_response(mode, level)

    t0 = time.time()
    try:
        client = _build_client()
        thinking_cfg = types.ThinkingConfig(
            thinking_level=level,
            include_thoughts=True,
        )

        if mode == "temporal_actions":
            prompt = custom_prompt.strip() or (
                "Analyze this 90-second industrial bicycle assembly video from OpenMARCIE (Vol10). "
                "Segment it into chronological action intervals with MM:SS timestamps, action labels, "
                "components/tools, worker posture, and visual evidence."
            )
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[
                    types.Part.from_bytes(data=CLIP_PATH.read_bytes(), mime_type="video/mp4"),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AssemblyTimeline,
                    thinking_config=thinking_cfg,
                ),
            )
            thoughts, text = _extract_thoughts_and_text(response)
            return {
                "mode": mode,
                "model": MODEL_ID,
                "thinking_level": level,
                "elapsed_sec": round(time.time() - t0, 2),
                "thoughts": thoughts,
                "result": json.loads(text),
            }

        if mode == "spatial_transitions":
            contents: list[Any] = []
            for label, path in KEYFRAMES:
                contents.append(f"Keyframe at {label}:")
                contents.append(types.Part.from_bytes(data=path.read_bytes(), mime_type="image/jpeg"))
            contents.append(
                custom_prompt.strip()
                or (
                    "Compare these three keyframes (t=00s, t=30s, t=60s) from OpenMARCIE Vol10. "
                    "Summarize changes in worker posture/position, bicycle assembly progress, "
                    "and any tool/workbench state transitions in clean Markdown."
                )
            )
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=contents,
                config=types.GenerateContentConfig(thinking_config=thinking_cfg),
            )
            thoughts, text = _extract_thoughts_and_text(response)
            return {
                "mode": mode,
                "model": MODEL_ID,
                "thinking_level": level,
                "elapsed_sec": round(time.time() - t0, 2),
                "thoughts": thoughts,
                "result": text,
            }

        # Default: ehs_audit
        prompt = custom_prompt.strip() or (
            "You are an Industrial Operations & EHS Auditor. Review this 90-second bicycle "
            "assembly clip from OpenMARCIE Vol10 and produce a concise Markdown audit report "
            "covering: 1) Ergonomics & Posture with timestamps, 2) PPE & Workspace Safety Hazards, "
            "and 3) Process Efficiency recommendations."
        )
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[
                types.Part.from_bytes(data=CLIP_PATH.read_bytes(), mime_type="video/mp4"),
                prompt,
            ],
            config=types.GenerateContentConfig(thinking_config=thinking_cfg),
        )
        thoughts, text = _extract_thoughts_and_text(response)
        return {
            "mode": "ehs_audit",
            "model": MODEL_ID,
            "thinking_level": level,
            "elapsed_sec": round(time.time() - t0, 2),
            "thoughts": thoughts,
            "result": text,
        }

    except Exception as exc:
        sim = get_simulated_response(mode, level)
        sim["fallback_reason"] = str(exc)
        return sim


# Demo Factory entrypoint naming convention
root_agent = {
    "name": "openmarcie_gemini_4_hydrogen",
    "model": MODEL_ID,
    "runner": run_multimodal_analysis,
}
app = root_agent
