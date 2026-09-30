"""ADK Agent Entrypoint for Acme Inc. Creative Studio MCP App.

Exposes `root_agent` and `app` at module level per Demo Factory and ADK standards.
"""

import os
from typing import Any


class Agent:
    """Standard ADK Agent representation for Acme Inc. Creative Studio."""

    def __init__(
        self,
        name: str,
        model: str,
        instruction: str,
        tools: list[Any] | None = None,
    ) -> None:
        self.name = name
        self.model = model
        self.instruction = instruction
        self.tools = tools or []


SYSTEM_INSTRUCTION = (
    "CRITICAL: You are the Acme Inc. Creative Studio Assistant in Gemini Enterprise. "
    "Whenever the user asks to open the creative studio, launch the ad studio, upload "
    "reference images/content, generate ad copy with Gemini Omni and Nano Banana, check "
    "active background jobs, or inspect/compare content versions in the GCS bucket, "
    "always call the `open_creative_studio` or corresponding MCP tool. "
    "Never route or transfer to canvas_agent, and do not create a generic markdown "
    "document in place of the interactive Creative Studio MCP App (`ui://acme/creative-studio`)."
)

GEMINI_OMNI_MODEL = os.environ.get("GEMINI_OMNI_MODEL", "gemini-omni-flash-preview")
NANO_BANANA_MODEL = os.environ.get("NANO_BANANA_MODEL", "gemini-3.1-flash-image-preview")

root_agent = Agent(
    name="acme-creative-studio-agent",
    model=GEMINI_OMNI_MODEL,
    instruction=SYSTEM_INSTRUCTION,
)

# ADK toolchain discovery alias
app = root_agent

