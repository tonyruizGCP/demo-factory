from abc import ABC, abstractmethod
from typing import Optional

try:
    from ..core.models import AgentTrajectory, ScenarioTask
    from ..harbor.sandbox import HarborSandbox
    from ..models.gemini_client import GeminiClient
except (ImportError, ValueError):
    from core.models import AgentTrajectory, ScenarioTask
    from harbor.sandbox import HarborSandbox
    from models.gemini_client import GeminiClient


class BaseAgentHarness(ABC):
    """Abstract base class for all threat-hunting agent harnesses."""

    def __init__(self, name: str, model_name: str = "gemini-3.7-flash", thinking_budget: int = 2048):
        self.name = name
        self.model_name = model_name
        self.thinking_budget = thinking_budget
        self.gemini_client = GeminiClient(model_name=model_name)

    @abstractmethod
    def run_investigation(
        self,
        scenario: ScenarioTask,
        sandbox: HarborSandbox,
        use_live_llm: bool = False,
    ) -> AgentTrajectory:
        """Execute a threat hunting investigation on the provided scenario within the sandbox."""
        pass
