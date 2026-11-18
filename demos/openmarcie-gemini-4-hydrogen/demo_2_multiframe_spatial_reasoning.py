"""Demo 2: Multi-Frame Spatial & State-Transition Reasoning."""

from pathlib import Path
from google.genai import types
from gemini_client import get_client


def main() -> None:
    clips_dir = Path(__file__).parent / "data" / "clips"
    frames = [
        ("t=00s", clips_dir / "cropped_00s.jpg"),
        ("t=30s", clips_dir / "cropped_30s.jpg"),
        ("t=60s", clips_dir / "cropped_60s.jpg"),
    ]

    contents: list = []
    for label, path in frames:
        contents.append(f"Keyframe at {label}:")
        contents.append(types.Part.from_bytes(data=path.read_bytes(), mime_type="image/jpeg"))

    contents.append(
        "Compare these three keyframes (t=00s, t=30s, t=60s) from the OpenMARCIE Vol10 "
        "bicycle assembly workspace. Describe:\n"
        "1. What changed in the worker's position and posture across the 3 frames.\n"
        "2. What physical assembly progress or state transitions occurred on the bicycle.\n"
        "3. Whether any tools, parts, or items on the green workbench or floor moved."
    )

    client = get_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.2),
    )

    print("=== Demo 2: Multi-Frame Spatial & State-Transition Reasoning ===")
    print(response.text)


if __name__ == "__main__":
    main()
