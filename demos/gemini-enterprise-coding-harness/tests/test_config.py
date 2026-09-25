"""Tests for HarnessConfig and configuration loading."""

import os
import pytest
from app.config import HarnessConfig


def test_default_config_is_local(monkeypatch):
  """Running without flags or env vars should default to 100% local mode."""
  for env_var in [
      "USE_MANAGED_SERVICES",
      "USE_MANAGED_SESSIONS",
      "USE_MANAGED_MEMORY_BANK",
  ]:
    monkeypatch.delenv(env_var, raising=False)

  cfg = HarnessConfig.from_env_and_args([])
  assert cfg.use_managed_services is False
  assert cfg.use_managed_sessions is None
  assert cfg.use_managed_memory_bank is None
  assert cfg.is_sessions_managed is False
  assert cfg.is_memory_bank_managed is False


def test_top_level_cli_flag():
  """--use-managed-services enables both sessions and memory bank."""
  cfg = HarnessConfig.from_env_and_args(["--use-managed-services"])
  assert cfg.use_managed_services is True
  assert cfg.is_sessions_managed is True
  assert cfg.is_memory_bank_managed is True


def test_top_level_env_var(monkeypatch):
  """USE_MANAGED_SERVICES=true enables both backends."""
  monkeypatch.setenv("USE_MANAGED_SERVICES", "true")
  cfg = HarnessConfig.from_env_and_args([])
  assert cfg.use_managed_services is True
  assert cfg.is_sessions_managed is True
  assert cfg.is_memory_bank_managed is True


def test_granular_override_sessions_only(monkeypatch):
  """USE_MANAGED_SESSIONS=true enables sessions while memory bank stays local."""
  monkeypatch.delenv("USE_MANAGED_SERVICES", raising=False)
  monkeypatch.setenv("USE_MANAGED_SESSIONS", "true")
  monkeypatch.delenv("USE_MANAGED_MEMORY_BANK", raising=False)

  cfg = HarnessConfig.from_env_and_args([])
  assert cfg.is_sessions_managed is True
  assert cfg.is_memory_bank_managed is False


def test_granular_override_memory_bank_only(monkeypatch):
  """USE_MANAGED_MEMORY_BANK=true enables memory bank while sessions stay local."""
  monkeypatch.delenv("USE_MANAGED_SERVICES", raising=False)
  monkeypatch.delenv("USE_MANAGED_SESSIONS", raising=False)
  monkeypatch.setenv("USE_MANAGED_MEMORY_BANK", "true")

  cfg = HarnessConfig.from_env_and_args([])
  assert cfg.is_sessions_managed is False
  assert cfg.is_memory_bank_managed is True


def test_granular_cli_disable_override():
  """--no-managed-sessions overrides top-level --use-managed-services."""
  cfg = HarnessConfig.from_env_and_args(
      ["--use-managed-services", "--no-managed-sessions"]
  )
  assert cfg.is_sessions_managed is False
  assert cfg.is_memory_bank_managed is True


def test_gcp_context_args():
  """GCP project, location, and agent engine ID are parsed from arguments."""
  cfg = HarnessConfig.from_env_and_args([
      "--project-id=custom-project",
      "--location=europe-west1",
      "--agent-engine-id=custom-engine-42",
  ])
  assert cfg.project_id == "custom-project"
  assert cfg.location == "europe-west1"
  assert cfg.agent_engine_id == "custom-engine-42"
