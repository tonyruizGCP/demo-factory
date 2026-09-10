# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ACME Inc Retail Data Analyst Agent.

An ADK agent that serves as the central analytical intelligence hub.
Dynamically discovers, loads, and executes modular skills from the
Gemini Enterprise Agent Platform Skill Registry.
"""

import os
from dotenv import load_dotenv

from google.adk import Agent
from google.adk.apps import App
from google.adk.code_executors import UnsafeLocalCodeExecutor
from google.adk.tools.skill_toolset import SkillToolset

from app.registry import get_skill_registry
from app.tools import query_store_sales, query_store_inventory, query_store_metadata

load_dotenv()

# Project & Region setup
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT", "truiz-agent-builder")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-2.5-flash")

# Initialize Enterprise Skill Registry connector
registry = get_skill_registry(project_id=PROJECT_ID, location=LOCATION)

# Initialize isolated code executor for skill scripts
code_executor = UnsafeLocalCodeExecutor()

# Initialize ADK SkillToolset bound to the Enterprise Registry
skill_toolset = SkillToolset(
    registry=registry,
    code_executor=code_executor
)

# Standard retail data tools
retail_tools = [
    query_store_sales,
    query_store_inventory,
    query_store_metadata,
    skill_toolset
]

AGENT_INSTRUCTION = """You are ACME Inc's primary Retail Data Analyst agent.
You assist retail store managers, district directors, and merchandise planners by analyzing store performance, inventory levels, and operational health.

CRITICAL OPERATIONAL BEHAVIORS:
1. When a user asks for a specific business evaluation, diagnostic, or recap:
   - Check available skills using `search_skills` or `list_skills`.
   - If a matching skill exists (such as `store-performance-review`, `daily-summary-recap`, or `inventory-optimization-audit`), you MUST load its instructions via `load_skill(skill_name)`.
   - Follow the loaded skill's workflow instructions strictly and systematically.
   - Use `load_skill_resource` to read reference rubrics or benchmark guides if mentioned in the skill.
   - Use `run_skill_script` to execute any computation or KPI calculation scripts bundled with the skill.
2. Execute data queries using `query_store_sales` and `query_store_inventory` to ground your calculations on real store metrics.
3. Deliver professional, data-backed insights with clear, prescriptive recommendations tailored to retail operations.
4. Format all tabular figures cleanly using markdown tables and include clear status indicators (🟢, 🟡, 🔴).
"""

# Root Agent Definition
root_agent = Agent(
    name="retail_data_analyst",
    model=MODEL_NAME,
    instruction=AGENT_INSTRUCTION,
    tools=retail_tools
)

# ADK Top-Level App Object (Required by ADK toolchain)
app = App(
    root_agent=root_agent,
    name="app"
)
