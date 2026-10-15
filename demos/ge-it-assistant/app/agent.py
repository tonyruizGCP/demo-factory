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

"""Enterprise IT Assistant ADK 2.0 Agent for Acme Co. (Gemini Enterprise).

Built on the `VeerMuchandi/Learn_ADK_Agents/ge_datastore_accessor_agent` blueprint
using ADK 2.0 (`google-adk>=2.0.0,<3.0.0`). Connects to the data stores and
federated connectors configured in Gemini Enterprise:
- Jira Cloud (`JIRA_DATA_STORE_ID` / project `SAM1`)
- Google Drive (`GDRIVE_DATA_STORE_ID`) & NotebookLM (`GNOTEBOOK_DATA_STORE_ID`)
- Gmail (`GMAIL_DATA_STORE_ID`) & Google Calendar (`GCAL_DATA_STORE_ID`)
- Salesforce Support Cases (`SF_CASE_DATA_STORE_ID`)
- GitHub Engineering (`GITHUB_REPO_DATA_STORE_ID` / `GITHUB_ISSUE_DATA_STORE_ID`)
"""

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field

from app.tools import (
    search_datastore_records,
    search_github_engineering,
    search_it_emails_and_calendar,
    search_it_knowledge_base,
    search_jira_tickets,
    search_salesforce_cases,
)

load_dotenv()

# Standardized execution budget per Gemini Enterprise Technical Deployment Runbook (Section 2.4.2)
EXECUTION_BUDGET_CONFIG = types.GenerateContentConfig(
    max_output_tokens=2048,
    temperature=0.1,
)


class JiraTriageReport(BaseModel):
    """Structured output returned by the Jira Ticket Specialist task sub-agent."""

    project_key: str = Field(description="The Jira project key inspected (e.g., SAM1).")
    queried_ticket_summary: str = Field(
        description="Detailed status, priority, issue type, assignee, and description of the requested ticket(s)."
    )
    open_tickets_breakdown: list[str] = Field(
        description="List of relevant open tickets formatted as 'KEY: Summary (Status | Priority | Type)'."
    )
    recommended_next_steps: str = Field(
        description="Actionable IT or engineering follow-up recommendations based on the ticket statuses."
    )


class WorkspaceITReport(BaseModel):
    """Structured output returned by the Workspace IT & Knowledge Base Specialist task sub-agent."""

    sources_searched: list[str] = Field(
        description="Connected Gemini Enterprise data stores queried (e.g., Google Drive, Gmail, Google Calendar)."
    )
    findings_summary: str = Field(
        description="Comprehensive summary of matching runbooks, documents, emails, or calendar events with exact titles, dates/times, and IDs."
    )
    key_artifacts: list[str] = Field(
        description="List of matching document titles, email subjects, or calendar event names with their details."
    )


class DevOpsCRMReport(BaseModel):
    """Structured output returned by the DevOps & CRM Escalation Specialist task sub-agent."""

    salesforce_cases_summary: str = Field(
        description="Summary of matching Salesforce support cases (CaseNumber, Subject, Status, Priority, Description)."
    )
    github_engineering_summary: str = Field(
        description="Summary of matching GitHub repositories and issues (full_name, description, URLs)."
    )


jira_ticket_specialist = Agent(
    name="jira_ticket_specialist",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=EXECUTION_BUDGET_CONFIG,
    mode="task",
    description=(
        "Task specialist for querying Jira tickets, sprint backlogs, bug statuses, "
        "and priority escalations in project SAM1 via the connected Jira datastore."
    ),
    instruction=(
        "You are the Jira Ticket Specialist for the Acme Co. Enterprise IT Assistant. "
        "Always call `search_jira_tickets` (typically with `project_key='SAM1'`) to retrieve "
        "live ticket data before answering. Report exact ticket keys (e.g., SAM1-23, SAM1-22, SAM1-7), "
        "their exact Status ('To Do', 'In Progress', 'In Review', 'Done'), Priority ('High', 'Medium', 'Low'), "
        "Issue Type ('Task', 'Epic'), and full summary."
    ),
    tools=[search_jira_tickets],
    output_schema=JiraTriageReport,
)

workspace_it_specialist = Agent(
    name="workspace_it_specialist",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=EXECUTION_BUDGET_CONFIG,
    mode="task",
    description=(
        "Task specialist for searching IT runbooks, resolution plans, and security docs in Google Drive, "
        "IT onboarding sessions on Google Calendar, and security/system notifications in Gmail."
    ),
    instruction=(
        "You are the Google Workspace & IT Knowledge Base Specialist for Acme Co. "
        "Use `search_it_knowledge_base` or `search_datastore_records` for Google Drive documents and runbooks, "
        "and `search_it_emails_and_calendar` for Gmail alerts and Google Calendar events. "
        "Always include exact document titles, sender/organizer details, and event timestamps."
    ),
    tools=[
        search_it_knowledge_base,
        search_it_emails_and_calendar,
        search_datastore_records,
    ],
    output_schema=WorkspaceITReport,
)

devops_crm_specialist = Agent(
    name="devops_crm_specialist",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=EXECUTION_BUDGET_CONFIG,
    mode="task",
    description=(
        "Task specialist for investigating Salesforce customer support cases and GitHub engineering "
        "repositories and issues connected to Gemini Enterprise."
    ),
    instruction=(
        "You are the DevOps & CRM Escalation Specialist for Acme Co. "
        "Use `search_salesforce_cases` to inspect customer support cases (such as Case 00001002 for GC5060) "
        "and `search_github_engineering` to inspect connected GitHub repositories and issues. "
        "Always report exact CaseNumbers, Statuses, Priorities, and repository names."
    ),
    tools=[search_salesforce_cases, search_github_engineering],
    output_schema=DevOpsCRMReport,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    generate_content_config=EXECUTION_BUDGET_CONFIG,
    description=(
        "Enterprise IT Assistant for Acme Co. on Gemini Enterprise. "
        "Provides unified IT helpdesk, Jira ticket tracking, Google Drive runbook search, "
        "IT calendar/email lookup, Salesforce support case correlation, and GitHub repository discovery."
    ),
    instruction="""You are the **Enterprise IT Assistant** for **Acme Co.** running on **Gemini Enterprise**.
Your mission is to help employees, IT engineers, and support leads resolve IT requests by querying the live connected Data Stores and Federated Connectors in the Gemini Enterprise app.

### Connected Data Stores & Tools at Your Disposal
1. **Jira Tickets (`search_jira_tickets`)**:
   - Connected to Jira Cloud project **`SAM1`** (*"(Example) Billing System Dev"*).
   - Always call `search_jira_tickets(query=..., project_key="SAM1")` when asked about Jira tickets, task statuses, priorities, or escalations (e.g., `SAM1-23`, `SAM1-22`, `SAM1-10`, `SAM1-7`).
2. **IT Knowledge Base & Google Drive (`search_it_knowledge_base` & `search_datastore_records`)**:
   - Connected to Google Drive and NotebookLM data stores.
   - Use for technical resolution plans, executive briefings, GTM preflight plans (e.g., `GC5060`), vendor security questionnaires, and architecture documents.
3. **IT Emails & Onboarding Calendar (`search_it_emails_and_calendar`)**:
   - Connected to Gmail and Google Calendar data stores.
   - Use `source_type="calendar"` for IT onboarding schedules (e.g., *IT Laptop Setup*, *30-Day Check-in with HR and Manager*, *Architecture Overview*, *Daily Mentor Pairing*).
   - Use `source_type="gmail"` for IT/security emails (e.g., Salesforce security token updates, Connected App security updates, Jira workspace notifications, work item `SAM1-9`).
4. **Salesforce Support Cases (`search_salesforce_cases`)**:
   - Connected to the Salesforce Case data store and federated connector.
   - Use for customer escalations and support cases (e.g., Case `00001002` on `GC5060` electrical wiring installation, Case `00001000`, Case `00001001`, Case `00001005`).
5. **GitHub Engineering (`search_github_engineering`)**:
   - Connected to GitHub repository and issue data stores.
   - Use for finding engineering repositories (e.g., `adk-salesforce-agent`, `ge-spark-gtm-demo`, `spark-demo-apps`, `a2ui`, `travel-planner`) and repository status issues.

### Operating Guidelines
- **Always Ground in Live Tool Calls**: Never guess or fabricate ticket IDs, statuses, dates, or document titles. Call the appropriate search tool(s) first. For cross-system questions (such as an escalation spanning Salesforce, Jira, and Google Drive), call all relevant search tools and synthesize the findings clearly.
- **Be Specific & Structured**:
   - For **Jira tickets**: Always include the exact Ticket Key (e.g., `SAM1-23`), its full Summary/Title (e.g., `'Escalation: GC5060 Electrical Wiring Installation Documentation'`), Status, and Priority.
   - For **Google Drive documents**: List all relevant matching document titles verbatim (including plans like `'GC5060 Technical Resolution & GTM Preflight Plan'`, `'GC5060 Pipeline Resolution Plan'`, and briefings like `'Executive Briefing: GC5060 Support Bottleneck & Pipeline Resolution'`).
   - For **Gmail & Google Calendar**: Report exact email subjects (e.g., `'Your new Salesforce security token'`, `'Finish creating work item SAM1-9'`, `'Welcome to your Jira workspace'`) and exact calendar event titles (e.g., `'IT Laptop Setup'`, `'30-Day Check-in with HR and Manager'`).
   - For **GitHub repositories**: Report the connected repository names (e.g., `adk-salesforce-agent`, `ge-spark-gtm-demo`, `spark-demo-apps`) along with their descriptions.
- **Read-Only by Default**: All tools are strictly read-only search operations across connected data stores.
""",
    tools=[
        search_datastore_records,
        search_jira_tickets,
        search_it_knowledge_base,
        search_it_emails_and_calendar,
        search_salesforce_cases,
        search_github_engineering,
    ],
    sub_agents=[
        jira_ticket_specialist,
        workspace_it_specialist,
        devops_crm_specialist,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
