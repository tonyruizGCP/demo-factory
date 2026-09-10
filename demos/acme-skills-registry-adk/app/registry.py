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

"""Skill Registry connector for ACME Inc.

Integrates with Google Cloud Gemini Enterprise Agent Platform Skill Registry
and provides automatic local fallback for hermetic offline testing and demos.
"""

from __future__ import annotations

import asyncio
import logging
import os
import pathlib
from typing import Any, Dict, List, Optional

from google.adk.skills import Skill, load_skill_from_dir, models
from google.adk.skills.skill_registry import SkillRegistry

logger = logging.getLogger("acme_retail_skills.registry")

LOCAL_SKILLS_DIR = pathlib.Path(__file__).parent.parent / "skills"


class ACMESkillRegistry(SkillRegistry):
    """Enterprise Skill Registry client supporting GCP Cloud Registry and Local Dev."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        skills_dir: Optional[pathlib.Path] = None,
        prefer_gcp: bool = False,
    ):
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.skills_dir = skills_dir or LOCAL_SKILLS_DIR
        self.prefer_gcp = prefer_gcp
        self._local_cache: Dict[str, Skill] = {}
        self._load_local_skills()

    def _load_local_skills(self):
        """Pre-loads local skills from disk."""
        if not self.skills_dir.exists():
            return
        for item in self.skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                try:
                    skill = load_skill_from_dir(item)
                    self._local_cache[skill.name] = skill
                    logger.info("Loaded skill '%s' from local directory.", skill.name)
                except Exception as e:
                    logger.warning("Failed loading skill from %s: %s", item, e)

    async def get_skill(self, *, name: str) -> Skill:
        """Fetches a skill by name from GCP Registry or local repository."""
        # 1. Check local cache first if available
        if name in self._local_cache:
            return self._local_cache[name]

        # 2. Try fetching from GCP if configured
        if self.prefer_gcp and self.project_id:
            try:
                from google.adk.integrations.skill_registry import GCPSkillRegistry
                gcp_reg = GCPSkillRegistry(project_id=self.project_id, location=self.location)
                remote_skill = await gcp_reg.get_skill(name=name)
                if remote_skill:
                    self._local_cache[name] = remote_skill
                    return remote_skill
            except Exception as e:
                logger.warning("GCP Skill Registry lookup failed for '%s': %s", name, e)

        raise ValueError(f"Skill '{name}' not found in ACME Skill Registry.")

    async def search_skills(self, *, query: str) -> list[models.Frontmatter]:
        """Searches skills matching a query string."""
        query_lower = query.lower()
        results: list[models.Frontmatter] = []

        # Check local catalog
        for skill in self._local_cache.values():
            name_match = query_lower in skill.name.lower()
            desc_match = query_lower in (skill.description or "").lower()
            
            # Match on semantic keywords for demo
            keywords = {
                "store-performance-review": ["store", "performance", "sales", "revenue", "review", "kpi", "labor", "traffic", "diagnostic"],
                "daily-summary-recap": ["daily", "summary", "recap", "morning", "huddle", "shift", "today", "yesterday", "flash"],
                "inventory-optimization-audit": ["inventory", "audit", "stock", "stockout", "shrinkage", "sku", "replenishment"]
            }
            keyword_match = any(kw in query_lower for kw in keywords.get(skill.name, []))

            if name_match or desc_match or keyword_match:
                results.append(skill.frontmatter)

        # Fallback to returning all skills if no strict match
        if not results:
            results = [s.frontmatter for s in self._local_cache.values()]

        return results

    def search_tool_description(self) -> str:
        return "Searches the ACME Enterprise Skill Registry for available analytical skills like store-performance-review, daily-summary-recap, and inventory-optimization-audit."

    def list_all_skills(self) -> List[Dict[str, Any]]:
        """Utility for dashboards and inspectors."""
        catalog = []
        for s in self._local_cache.values():
            catalog.append({
                "name": s.name,
                "description": s.description,
                "scripts": s.resources.list_scripts(),
                "references": s.resources.list_references(),
                "instructions_preview": s.instructions[:250] + "..." if len(s.instructions) > 250 else s.instructions,
                "full_instructions": s.instructions
            })
        return catalog


def get_skill_registry(project_id: Optional[str] = None, location: Optional[str] = None) -> ACMESkillRegistry:
    """Factory method returning initialized ACMESkillRegistry."""
    return ACMESkillRegistry(project_id=project_id, location=location)
