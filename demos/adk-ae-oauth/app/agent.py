import os
from app.tools import read_drive_file

try:
    import google.auth
    _, project_id = google.auth.default()
except Exception:
    project_id = "demo-gcp-project"

# Enforce Demo Factory rule: Use GCP_PROJECT instead of reserved GOOGLE_CLOUD_PROJECT
os.environ["GCP_PROJECT"] = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT", project_id)
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

try:
    from google.adk.agents import Agent
    from google.adk.apps import App
    from google.adk.models import Gemini
    from google.genai import types

    root_agent = Agent(
        name="root_agent",
        model=Gemini(
            model="gemini-2.5-flash",
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        instruction="""You are a specialized enterprise assistant that reads Google Drive files via OAuth 2.0.

When a user asks to inspect or read a Google Drive document:
1. Identify the file ID (the alphanumeric string in the Google Drive URL).
2. Call the read_drive_file tool.
3. If authentication status is pending, instruct the user to complete OAuth consent.
4. Provide a clear summary and key insights of the retrieved document.
""",
        tools=[read_drive_file],
    )

    app = App(
        root_agent=root_agent,
        name="app",
    )
except ImportError:
    class DummyAgent:
        def __init__(self, name, instruction):
            self.name = name
            self.instruction = instruction
    root_agent = DummyAgent("adk-oauth-agent", "Google Drive Reader with OAuth 2.0")
    app = root_agent
