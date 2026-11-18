"""Selectively download a tiny subset of OpenMARCIE (Vol10) from Kaggle.

Avoids downloading the full 197 GB OpenMarcieA_Main dataset by fetching only
one exocentric RGB video (~152 MB) and extracting a cropped 90-second clip
plus keyframes for Gemini multimodal demos.
"""

import os
import subprocess
from pathlib import Path
import kagglehub

DATASET_HANDLE = "openmarciea/openmarciea-again"
VIDEO_PATH = (
    "Vol10/ExoData/ExoVideoVol10/ExoVideoVol10/"
    "PositionWindow/BikeExoWindowVol10_RGB_anonymized.mp4"
)


def ensure_kaggle_token() -> None:
    if os.environ.get("KAGGLE_API_TOKEN"):
        return
    token_file = Path.home() / ".kaggle" / "access_token"
    if token_file.exists():
        os.environ["KAGGLE_API_TOKEN"] = token_file.read_text().strip()
    else:
        raise RuntimeError(
            "Set KAGGLE_API_TOKEN or place your Kaggle token at ~/.kaggle/access_token"
        )


def main() -> None:
    ensure_kaggle_token()
    base_dir = Path(__file__).parent
    raw_dir = base_dir / "data" / "vol10"
    clips_dir = base_dir / "data" / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading selective file: {VIDEO_PATH}")
    downloaded = Path(
        kagglehub.dataset_download(
            DATASET_HANDLE,
            path=VIDEO_PATH,
            output_dir=str(raw_dir),
        )
    )
    print(f"Downloaded to: {downloaded}")

    clip_90s = clips_dir / "vol10_window_90s.mp4"
    clip_cropped = clips_dir / "vol10_window_90s_cropped.mp4"

    if not clip_90s.exists():
        subprocess.run(
            [
                "ffmpeg", "-y", "-ss", "00:05:00", "-t", "90",
                "-i", str(downloaded), "-c", "copy", str(clip_90s),
                "-loglevel", "error",
            ],
            check=True,
        )

    if not clip_cropped.exists():
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(clip_90s),
                "-vf", "crop=360:266:180:106",
                "-c:v", "libx264", "-crf", "22", str(clip_cropped),
                "-loglevel", "error",
            ],
            check=True,
        )

    for sec in (0, 30, 60):
        out_img = clips_dir / f"cropped_{sec:02d}s.jpg"
        if not out_img.exists():
            subprocess.run(
                [
                    "ffmpeg", "-y", "-ss", str(sec),
                    "-i", str(clip_cropped), "-frames:v", "1", str(out_img),
                    "-loglevel", "error",
                ],
                check=True,
            )

    print(f"Ready! Cropped 90s clip: {clip_cropped} ({clip_cropped.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
