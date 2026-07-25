import os
from google.genai import types

# Standard ADK Agent export entrypoint
class Agent:
    def __init__(self, name: str, instruction: str):
        self.name = name
        self.instruction = instruction

root_agent = Agent(
    name="test-healthcare-triage-agent",
    instruction="You are a specialized agent for Test Healthcare Triage Assistant built with ADK 2.0 + FastAPI + Vertex AI."
)
app = root_agent
