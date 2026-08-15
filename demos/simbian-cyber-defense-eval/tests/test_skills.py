"""Unit tests for SkillsRegistry and AGENTS.md loader."""

from pathlib import Path
from core.skills_loader import SkillsRegistry


def test_skills_registry_loading():
    registry = SkillsRegistry()
    skills = registry.get_skills_list()
    assert len(skills) >= 7

    skill_ids = [s["skill_id"] for s in skills]
    assert "attack_surface_mapping" in skill_ids
    assert "telemetry_sql_analyst" in skill_ids
    assert "mitre_attack_classifier" in skill_ids
    assert "vulnerability_validator" in skill_ids
    assert "cve_code_analyzer" in skill_ids
    assert "false_positive_pruner" in skill_ids
    assert "patch_remediation_generator" in skill_ids


def test_agents_spec_markdown():
    registry = SkillsRegistry()
    md = registry.get_agents_spec_markdown()
    assert "# ACME AI Security Auditing" in md
    assert "Lead Security Orchestrator" in md


def test_prompt_context_generation():
    registry = SkillsRegistry()
    prompt_ctx = registry.generate_harness_prompt_context()
    assert "ACTIVE MULTI-AGENT SPECIALIST SKILLS & WEIGHTS" in prompt_ctx
    assert "Telemetry SQL Analyst" in prompt_ctx
