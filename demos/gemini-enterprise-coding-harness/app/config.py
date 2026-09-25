"""Configuration module for Gemini Enterprise Coding Harness.

Manages configuration for Vertex AI Memory Bank and Gemini Enterprise / ADK Sessions,
supporting top-level flags, granular overrides, and environment variables.
"""

import os
import sys
from typing import List, Optional
from pydantic import BaseModel, Field


def _is_truthy(val: Optional[str]) -> Optional[bool]:
  if val is None:
    return None
  v = val.strip().lower()
  if v in ("true", "1", "yes", "on"):
    return True
  if v in ("false", "0", "no", "off"):
    return False
  return None


class HarnessConfig(BaseModel):
  """Runtime configuration for Gemini Enterprise Coding Harness."""

  use_managed_services: bool = False
  use_managed_sessions: Optional[bool] = None
  use_managed_memory_bank: Optional[bool] = None
  project_id: str = "truiz-agy-demo"
  location: str = "us-central1"
  agent_engine_id: str = "coding-harness-engine"

  @property
  def is_sessions_managed(self) -> bool:
    """Returns whether sessions should use managed VertexAiSessionService."""
    if self.use_managed_sessions is not None:
      return self.use_managed_sessions
    return self.use_managed_services

  @property
  def is_memory_bank_managed(self) -> bool:
    """Returns whether memory bank should use managed MemoryBankServiceClient."""
    if self.use_managed_memory_bank is not None:
      return self.use_managed_memory_bank
    return self.use_managed_services

  @classmethod
  def from_env_and_args(
      cls, args: Optional[List[str]] = None
  ) -> "HarnessConfig":
    """Builds configuration from environment variables and CLI arguments."""
    # 1. Parse environment variables
    env_managed_services = _is_truthy(os.environ.get("USE_MANAGED_SERVICES"))
    env_managed_sessions = _is_truthy(os.environ.get("USE_MANAGED_SESSIONS"))
    env_managed_memory = _is_truthy(os.environ.get("USE_MANAGED_MEMORY_BANK"))

    project_id = (
        os.environ.get("GCP_PROJECT")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or "truiz-agy-demo"
    )
    location = (
        os.environ.get("GOOGLE_CLOUD_LOCATION")
        or os.environ.get("GCP_LOCATION")
        or "us-central1"
    )
    agent_engine_id = (
        os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID")
        or os.environ.get("AGENT_ENGINE_ID")
        or "coding-harness-engine"
    )

    # 2. Process command-line arguments if provided or from sys.argv
    cli_args = args if args is not None else sys.argv[1:]
    cli_managed_services: Optional[bool] = None
    cli_managed_sessions: Optional[bool] = None
    cli_managed_memory: Optional[bool] = None

    i = 0
    while i < len(cli_args):
      arg = cli_args[i]
      if arg == "--use-managed-services":
        cli_managed_services = True
      elif arg == "--no-managed-services":
        cli_managed_services = False
      elif arg == "--use-managed-sessions":
        cli_managed_sessions = True
      elif arg == "--no-managed-sessions":
        cli_managed_sessions = False
      elif arg == "--use-managed-memory-bank":
        cli_managed_memory = True
      elif arg == "--no-managed-memory-bank":
        cli_managed_memory = False
      elif arg == "--project-id" and i + 1 < len(cli_args):
        i += 1
        project_id = cli_args[i]
      elif arg.startswith("--project-id="):
        project_id = arg.split("=", 1)[1]
      elif arg == "--location" and i + 1 < len(cli_args):
        i += 1
        location = cli_args[i]
      elif arg.startswith("--location="):
        location = arg.split("=", 1)[1]
      elif arg == "--agent-engine-id" and i + 1 < len(cli_args):
        i += 1
        agent_engine_id = cli_args[i]
      elif arg.startswith("--agent-engine-id="):
        agent_engine_id = arg.split("=", 1)[1]
      i += 1

    # 3. Resolve precedence: CLI granular > CLI top-level > Env granular > Env top-level > False
    if cli_managed_services is not None:
      use_managed_services = cli_managed_services
    elif env_managed_services is not None:
      use_managed_services = env_managed_services
    else:
      use_managed_services = False

    # Granular sessions resolution
    if cli_managed_sessions is not None:
      use_managed_sessions = cli_managed_sessions
    elif cli_managed_services is not None:
      use_managed_sessions = cli_managed_services
    elif env_managed_sessions is not None:
      use_managed_sessions = env_managed_sessions
    elif env_managed_services is not None:
      use_managed_sessions = env_managed_services
    else:
      use_managed_sessions = None

    # Granular memory bank resolution
    if cli_managed_memory is not None:
      use_managed_memory_bank = cli_managed_memory
    elif cli_managed_services is not None:
      use_managed_memory_bank = cli_managed_services
    elif env_managed_memory is not None:
      use_managed_memory_bank = env_managed_memory
    elif env_managed_services is not None:
      use_managed_memory_bank = env_managed_services
    else:
      use_managed_memory_bank = None

    return cls(
        use_managed_services=use_managed_services,
        use_managed_sessions=use_managed_sessions,
        use_managed_memory_bank=use_managed_memory_bank,
        project_id=project_id,
        location=location,
        agent_engine_id=agent_engine_id,
    )


_GLOBAL_CONFIG: Optional[HarnessConfig] = None


def get_config(reload: bool = False) -> HarnessConfig:
  """Returns the global application configuration."""
  global _GLOBAL_CONFIG
  if _GLOBAL_CONFIG is None or reload:
    _GLOBAL_CONFIG = HarnessConfig.from_env_and_args()
  return _GLOBAL_CONFIG


def set_config(config: HarnessConfig) -> None:
  """Sets the global application configuration."""
  global _GLOBAL_CONFIG
  _GLOBAL_CONFIG = config
