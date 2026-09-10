#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Publishes ACME retail skills to the Gemini Enterprise Agent Platform Skill Registry."""

import argparse
import base64
import io
import os
import pathlib
import sys
import zipfile
import requests
import google.auth
import google.auth.transport.requests

ROOT_DIR = pathlib.Path(__file__).parent.parent
SKILLS_DIR = ROOT_DIR / "skills"


def get_auth_headers() -> dict:
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    return {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }


def zip_skill_directory(skill_folder: pathlib.Path) -> str:
    """Zips a skill directory into a base64 encoded string."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for file_path in skill_folder.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                arcname = file_path.relative_to(skill_folder)
                z.write(file_path, arcname=str(arcname))
    zip_buffer.seek(0)
    return base64.b64encode(zip_buffer.read()).decode("utf-8")


def parse_skill_metadata(skill_folder: pathlib.Path) -> dict:
    """Extracts frontmatter metadata from SKILL.md."""
    skill_md = skill_folder / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md missing in {skill_folder}")

    text = skill_md.read_text(encoding="utf-8")
    meta = {"name": skill_folder.name, "description": "", "display_name": skill_folder.name}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if line.startswith("name:"):
                    meta["name"] = line.split(":", 1)[1].strip().strip('"')
                elif line.startswith("description:"):
                    meta["description"] = line.split(":", 1)[1].strip().strip('"')
    return meta


def publish_skill(project_id: str, location: str, skill_folder: pathlib.Path, dry_run: bool = False):
    meta = parse_skill_metadata(skill_folder)
    skill_id = meta["name"]
    base64_zip = zip_skill_directory(skill_folder)

    print(f"📦 Packaging skill: {skill_id} ({skill_folder.name})")
    print(f"   Description: {meta['description'][:80]}...")
    print(f"   Payload size: {len(base64_zip)} base64 characters")

    if dry_run:
        print(f"   [DRY-RUN] Would upload {skill_id} to projects/{project_id}/locations/{location}/skills/{skill_id}")
        return True

    endpoint = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/{location}/skills"
    headers = get_auth_headers()

    # Check if skill exists
    check_url = f"{endpoint}/{skill_id}"
    check_res = requests.get(check_url, headers=headers)

    payload = {
        "displayName": meta["name"],
        "description": meta["description"],
        "zippedFilesystem": base64_zip
    }

    if check_res.status_code == 200:
        print(f"   Skill '{skill_id}' already exists. Performing PATCH update...")
        patch_url = f"{check_url}?updateMask=displayName,description,zippedFilesystem"
        res = requests.patch(patch_url, json=payload, headers=headers)
    else:
        print(f"   Skill '{skill_id}' does not exist. Performing POST creation...")
        create_url = f"{endpoint}?skillId={skill_id}"
        res = requests.post(create_url, json=payload, headers=headers)

    if res.status_code in [200, 201]:
        print(f"   ✅ Successfully published '{skill_id}' to Skill Registry!")
        return True
    else:
        print(f"   ❌ Upload failed ({res.status_code}): {res.text}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Publish skills to Agent Platform Skill Registry.")
    parser.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT", "truiz-agent-builder"), help="GCP Project ID")
    parser.add_argument("--location", default=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"), help="GCP Location")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without calling GCP APIs")
    parser.add_argument("--skill", default="all", help="Specific skill name or 'all'")

    args = parser.parse_args()

    skills_to_publish = []
    if args.skill == "all":
        skills_to_publish = [d for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
    else:
        target = SKILLS_DIR / args.skill
        if target.exists() and target.is_dir():
            skills_to_publish = [target]
        else:
            print(f"Skill directory {target} not found.")
            sys.exit(1)

    print(f"🚀 Publishing {len(skills_to_publish)} skills to GCP Project: {args.project} ({args.location})")
    for s in skills_to_publish:
        publish_skill(args.project, args.location, s, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
