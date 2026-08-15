"""Skills & AGENTS.md Loader for Cyber Defense Harnesses.

Parses AGENTS.md multi-agent specifications and individual SKILL.md files
from the skills/ directory to dynamically build system prompts and tool contracts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class SkillDefinition:
    """Parsed representation of an agent skill."""

    def __init__(
        self,
        skill_id: str,
        name: str,
        description: str,
        role: str,
        weight: float,
        content: str,
        file_path: Path,
    ):
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.role = role
        self.weight = weight
        self.content = content
        self.file_path = file_path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "role": self.role,
            "weight": self.weight,
            "file_path": str(self.file_path),
        }


class SkillsRegistry:
    """Registry that discovers and manages skills and AGENTS.md."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path(__file__).resolve().parent.parent
        self.agents_file = self.root_dir / "AGENTS.md"
        self.skills_dir = self.root_dir / "skills"
        self._skills: Dict[str, SkillDefinition] = {}
        self.load_all()

    def load_all(self) -> None:
        """Scan skills directory and load all SKILL.md definitions."""
        self._skills.clear()
        if not self.skills_dir.exists():
            return

        for skill_folder in self.skills_dir.iterdir():
            if not skill_folder.is_dir():
                continue
            skill_md = skill_folder / "SKILL.md"
            if skill_md.exists():
                skill_def = self._parse_skill_file(skill_md, skill_folder.name)
                if skill_def:
                    self._skills[skill_def.skill_id] = skill_def

    def _parse_skill_file(self, file_path: Path, folder_name: str) -> Optional[SkillDefinition]:
        """Extract YAML frontmatter and markdown body from SKILL.md."""
        try:
            raw_text = file_path.read_text(encoding="utf-8")
            frontmatter = {}
            body = raw_text

            if raw_text.startswith("---"):
                parts = raw_text.split("---", 2)
                if len(parts) >= 3:
                    yaml_lines = parts[1].strip().split("\n")
                    body = parts[2].strip()
                    for yl in yaml_lines:
                        if ":" in yl:
                            k, v = yl.split(":", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k == "weight":
                                try:
                                    frontmatter[k] = float(v)
                                except Exception:
                                    frontmatter[k] = 1.0
                            else:
                                frontmatter[k] = v

            return SkillDefinition(
                skill_id=folder_name,
                name=frontmatter.get("name", folder_name),
                description=frontmatter.get("description", "Cyber defense skill"),
                role=frontmatter.get("role", "Security Specialist"),
                weight=frontmatter.get("weight", 1.0),
                content=body,
                file_path=file_path,
            )
        except Exception:
            return None

    def get_skills_list(self) -> List[Dict[str, Any]]:
        """Return list of loaded skills metadata."""
        return [s.to_dict() for s in sorted(self._skills.values(), key=lambda x: -x.weight)]

    def get_agents_spec_markdown(self) -> str:
        """Return the raw AGENTS.md content."""
        if self.agents_file.exists():
            return self.agents_file.read_text(encoding="utf-8")
        return ""

    def generate_harness_prompt_context(self) -> str:
        """Generate structured skills instructions to inject into LLM system prompts."""
        lines = [
            "### ACTIVE MULTI-AGENT SPECIALIST SKILLS & WEIGHTS:",
            "The team consists of specialized sub-agent roles. Coordinate across these skills during the investigation:",
        ]
        for skill in sorted(self._skills.values(), key=lambda x: -x.weight):
            lines.append(f"- **{skill.role}** (`{skill.name}`, Weight: {skill.weight}): {skill.description}")
        return "\n".join(lines)
