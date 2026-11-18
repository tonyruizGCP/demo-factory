"""Demo 3: Automated Industrial SOP & Safety (EHS) Audit."""

from pathlib import Path
from google.genai import types
from gemini_client import get_client


def main() -> None:
    clip_path = Path(__file__).parent / "data" / "clips" / "vol10_window_90s_cropped.mp4"
    video_bytes = clip_path.read_bytes()

    client = get_client()
    prompt = (
        "You are an Industrial Operations & EHS (Environment, Health, and Safety) Auditor. "
        "Review this 90-second bicycle assembly clip from OpenMARCIE Vol10 and produce a concise "
        "Markdown audit report covering:\n"
        "1. **Ergonomics & Posture**: Note prolonged bending/crouching or awkward reach with timestamps.\n"
        "2. **PPE & Safety Observations**: Comment on visible PPE (gloves, footwear, eyewear) and "
        "workspace floor/trip hazards.\n"
        "3. **Process Efficiency**: Identify any idle time, unnecessary walking between the bike stand "
        "and workbench/shelves, and 2 concrete recommendations to improve cycle time or safety."
    )

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[
            types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
            prompt,
        ],
        config=types.GenerateContentConfig(temperature=0.2),
    )

    print("=== Demo 3: Industrial SOP & Safety Audit ===")
    print(response.text)


if __name__ == "__main__":
    main()
