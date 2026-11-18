"""Demo 1: Video Temporal Action Recognition with Structured JSON Output."""

from pathlib import Path
from pydantic import BaseModel, Field
from google.genai import types
from gemini_client import MODEL_ID, get_client


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


def main() -> None:
    clip_path = Path(__file__).parent / "data" / "clips" / "vol10_window_90s_cropped.mp4"
    video_bytes = clip_path.read_bytes()

    client = get_client()
    prompt = (
        "Analyze this 90-second industrial bicycle assembly video from the OpenMARCIE dataset (Vol10). "
        "Segment the video into chronological action intervals. For each interval, identify the "
        "start/end timestamp (MM:SS), the specific assembly action, bicycle components/tools involved, "
        "the worker's posture, and brief visual evidence."
    )

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=[
            types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AssemblyTimeline,
            thinking_config=types.ThinkingConfig(thinking_level="MEDIUM", include_thoughts=True),
        ),
    )

    print("=== Demo 1: Temporal Action Recognition ===")
    print(response.text)


if __name__ == "__main__":
    main()
