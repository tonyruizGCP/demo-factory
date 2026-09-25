"""Sandbox configuration schema for Harbor isolated execution environments."""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SandboxConfig(BaseModel):
    """Configuration options for sandbox trial execution."""

    model_config = ConfigDict(extra="allow")

    timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        description="Watchdog timeout deadline in seconds",
    )
    timeout_sec: float = Field(
        default=30.0,
        gt=0.0,
        description="Watchdog timeout deadline in seconds (alias for timeout_seconds)",
    )
    memory_limit_mb: Optional[int] = Field(
        default=512,
        description="Memory ceiling in megabytes",
    )
    env_vars: Dict[str, str] = Field(
        default_factory=dict,
        description="Execution environment variables passed into sandbox",
    )
    work_dir: Optional[str] = Field(
        default=None,
        description="Explicit working directory; if None, an ephemeral directory is used",
    )
    cleanup: bool = Field(
        default=True,
        description="Whether to clean up ephemeral working directories after trial completion",
    )

    @model_validator(mode="before")
    @classmethod
    def sync_timeout(cls, values: Any) -> Any:
        if isinstance(values, dict):
            sec = values.get("timeout_sec")
            seconds = values.get("timeout_seconds")
            if sec is not None and seconds is None:
                values["timeout_seconds"] = float(sec)
                values["timeout_sec"] = float(sec)
            elif seconds is not None and sec is None:
                values["timeout_sec"] = float(seconds)
                values["timeout_seconds"] = float(seconds)
            elif sec is not None and seconds is not None:
                values["timeout_seconds"] = float(sec)
                values["timeout_sec"] = float(sec)
        return values
