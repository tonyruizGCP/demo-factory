"""Harbor task specification and trial configuration models.

Implements Harbor framework (harbor-framework/harbor) task definitions
and execution schemas for cyber defense agent benchmarking.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HarborEnvironmentConfig(BaseModel):
    """Harbor sandbox environment container and resource configuration."""
    image: str = "harbor-secops-sandbox:latest"
    sandbox_mode: str = Field(default="local-isolated", description="local-isolated, docker, or cloud-sandbox")
    timeout_seconds: int = 120
    memory_limit_mb: int = 2048
    cpu_limit_cores: float = 2.0
    network_egress: bool = False  # Egress blocked per security sandbox rules
    read_only_root_fs: bool = True
    env_vars: Dict[str, str] = Field(default_factory=dict)


class HarborTaskSpec(BaseModel):
    """Standardized Harbor task specification for a threat-hunting trial."""
    task_id: str = Field(..., description="Unique Harbor task identifier")
    benchmark_name: str = "simbian-cyber-defense"
    scenario_id: str = Field(..., description="Underlying scenario ID")
    instruction: str = Field(..., description="Task objective prompt given to the agent")
    environment: HarborEnvironmentConfig = Field(default_factory=HarborEnvironmentConfig)
    eval_verifier_script: str = "python verifier.py --task-id {task_id}"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HarborTrialJob(BaseModel):
    """Execution trial tracking an agent's run on a Harbor task."""
    trial_id: str
    task_spec: HarborTaskSpec
    agent_harness: str
    model_name: str
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, TIMED_OUT
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    sandbox_logs: List[str] = Field(default_factory=list)
    result_metadata: Dict[str, Any] = Field(default_factory=dict)
