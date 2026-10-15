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

"""DatastoreService and connected IT Assistant tools for Gemini Enterprise.

Follows the VeerMuchandi/Learn_ADK_Agents/ge_datastore_accessor_agent blueprint:
1. Extracts the user's OAuth access token from `tool_context.state.get(AUTH_NAME)`
   (or `temp:{AUTH_NAME}`) when invoked from Gemini Enterprise, with automatic
   fallback to Secret Manager / OAuth refresh credentials or Application Default
   Credentials (ADC) for local CLI runs, unit/integration tests, and evals.
2. Queries connected Discovery Engine Data Stores via `DatastoreService.search_datastore`
   (`.../collections/default_collection/dataStores/{datastore_id}/servingConfigs/default_search:search`).
3. Supports Third-Party Federated Connectors (`Jira`, `Salesforce`, `GitHub`) where
   `autoRunDisabled: true` by acquiring the live connector token via
   `dataConnector:acquireAccessToken` using the same user/ADC credential context.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import google.auth
import google.auth.transport.requests
import requests
from dotenv import load_dotenv
from google.adk.auth.auth_schemes import CustomAuthScheme
from google.adk.tools import ToolContext
from google.oauth2.credentials import Credentials
from pydantic import Field

load_dotenv()

logger = logging.getLogger(__name__)


class GcpAuthProviderScheme(CustomAuthScheme):
    """ADK 2.0 Agent Identity Auth Manager authentication scheme (`gcpAuthProviderScheme`)."""

    type_: str = Field(default="gcpAuthProviderScheme", alias="type")
    name: str
    scopes: list[str] | None = None
    continue_uri: str | None = None


# Default configuration for Acme Co. Gemini Enterprise IT Assistant Demo
DEFAULT_PROJECT_ID = "acme-enterprise-demo"
DEFAULT_PROJECT_NUMBER = "123456789012"
DEFAULT_LOCATION = "global"
DEFAULT_GE_APP_ID = "acme_ge_app"
DEFAULT_AUTH_NAME = "it_assistant_oauth_token"
DEFAULT_AUTH_PROVIDER_NAME = "projects/acme-enterprise-demo/locations/us-central1/authProviders/ge-it-assistant-oauth"
DEFAULT_CONTINUE_URI = "https://vertexaisearch.cloud.google.com"

DEFAULT_GDRIVE_DS = "acme-gdrive-ds_google_drive"
DEFAULT_GNOTEBOOK_DS = "acme-gnotebook-ds"
DEFAULT_GMAIL_DS = "acme-gmail-ds_google_mail"
DEFAULT_GCAL_DS = "acme-gcal-ds_google_calendar"

DEFAULT_JIRA_DS = "acme-jira-conn_issue"
DEFAULT_JIRA_COLLECTION = "acme-jira-conn"
DEFAULT_JIRA_CLOUD_ID = "00000000-0000-0000-0000-000000000000"
DEFAULT_JIRA_PROJECT = "SAM1"
DEFAULT_JIRA_BROWSE_URL = "https://acme-co.atlassian.net/browse"

DEFAULT_SF_CASE_DS = "acme-sf-connector_case"
DEFAULT_SF_ACCOUNT_DS = "acme-sf-connector_account"
DEFAULT_SF_COLLECTION = "acme-sf-connector"
DEFAULT_SF_INSTANCE_URL = "https://acme-co-dev-ed.develop.my.salesforce.com"

DEFAULT_GH_ISSUE_DS = "acme-github-ds_issue"
DEFAULT_GH_REPO_DS = "acme-github-ds_repository"
DEFAULT_GH_COLLECTION = "acme-github-ds"


def _get_project_id() -> str:
    return (
        os.getenv("GCP_PROJECT")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or DEFAULT_PROJECT_ID
    )


def _get_location() -> str:
    return os.getenv("DISCOVERY_ENGINE_LOCATION") or DEFAULT_LOCATION


def get_gcp_auth_provider_scheme() -> GcpAuthProviderScheme:
    """Returns the ADK 2.0 GcpAuthProviderScheme for Agent Identity Auth Manager."""
    provider_name = os.getenv("GCP_AUTH_PROVIDER_NAME") or DEFAULT_AUTH_PROVIDER_NAME
    continue_uri = os.getenv("GCP_AUTH_CONTINUE_URI") or DEFAULT_CONTINUE_URI
    return GcpAuthProviderScheme(
        name=provider_name,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
        continue_uri=continue_uri,
    )


def _retrieve_token_from_auth_manager(
    tool_context: ToolContext | None = None,
) -> str | None:
    """Retrieves an ephemeral end-user OAuth token via Agent Identity Auth Manager.

    Calls `https://agentidentitycredentials.googleapis.com/v1/{auth_provider}/credentials:retrieve`
    using the agent's workload identity (SPIFFE ID `principal://agents.global.org-...`
    with `roles/agentidentity.user`). This avoids persisting raw user OAuth tokens in
    `tool_context.state` when the user has already granted consent to the AuthProvider.
    """
    auth_provider = os.getenv("GCP_AUTH_PROVIDER_NAME")
    if not auth_provider:
        return None

    user_id = os.getenv("DEFAULT_AUTH_USER_ID") or "admin@acme-co.example.com"
    if tool_context is not None:
        ctx_user_id = getattr(tool_context, "user_id", None)
        if isinstance(ctx_user_id, str) and ctx_user_id.strip():
            user_id = ctx_user_id.strip()

    try:
        creds, _ = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        if not creds.token:
            return None

        scheme = get_gcp_auth_provider_scheme()
        url = f"https://agentidentitycredentials.googleapis.com/v1/{scheme.name}/credentials:retrieve"
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": "application/json",
                "X-Goog-User-Project": _get_project_id(),
            },
            json={
                "userId": user_id,
                "scopes": scheme.scopes
                or ["https://www.googleapis.com/auth/cloud-platform"],
                "continueUri": scheme.continue_uri or DEFAULT_CONTINUE_URI,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            success = data.get("success") or {}
            token = success.get("token")
            if isinstance(token, str) and token.strip():
                return token.strip()
            if "uriConsentRequired" in data:
                logger.info(
                    "Agent Identity Auth Manager requires initial 3LO consent for user %s at %s",
                    user_id,
                    data["uriConsentRequired"].get("authorizationUri"),
                )
    except Exception as e:
        logger.debug("Agent Identity Auth Manager lookup skipped/fallback: %s", e)
    return None


def _extract_access_token(tool_context: ToolContext | None) -> str | None:
    """Extracts the OAuth access token via Agent Identity Auth Manager or ADK ToolContext state."""
    # Tier 1: Agent Identity Auth Manager (zero state token exposure when consented)
    broker_token = _retrieve_token_from_auth_manager(tool_context)
    if broker_token:
        return broker_token

    # Tier 2: Gemini Enterprise OAuth token passed in ADK ToolContext state
    if tool_context is None or not hasattr(tool_context, "state"):
        return None
    auth_name = os.getenv("AUTH_NAME") or DEFAULT_AUTH_NAME
    for candidate_key in (
        auth_name,
        f"temp:{auth_name}",
        "access_token",
        "temp:access_token",
    ):
        token = tool_context.state.get(candidate_key)
        if isinstance(token, str) and token.strip():
            return token.strip()
        if isinstance(token, dict) and token.get("access_token"):
            return str(token["access_token"]).strip()

    # Also inspect dynamic OAuth token keys injected by Gemini Enterprise (including temp:* keys)
    try:
        state_dict = (
            tool_context.state.to_dict()
            if hasattr(tool_context.state, "to_dict")
            else dict(tool_context.state)
        )
        for key, value in state_dict.items():
            if isinstance(key, str) and (
                auth_name in key or "oauth" in key.lower() or "token" in key.lower()
            ):
                if isinstance(value, str) and len(value.strip()) > 20:
                    return value.strip()
                if isinstance(value, dict) and value.get("access_token"):
                    return str(value["access_token"]).strip()
    except Exception:
        pass
    return None


def _get_user_oauth_token() -> str | None:
    """Refreshes a user OAuth access token from environment credentials when available.

    In Vertex AI Agent Runtime containers, `google.auth.default()` resolves to the
    Reasoning Engine service account (`service-<project_number>@gcp-sa-aiplatform-re...`),
    which is not a Workspace/3LO user identity and receives 401/403 from ACL-protected
    Discovery Engine data stores and `dataConnector:acquireAccessToken`. When
    `USER_OAUTH_REFRESH_TOKEN` (or `OAUTH_ACCESS_TOKEN`) is configured on the runtime,
    this helper mints a fresh user OAuth token for seamless 3LO connector access.
    """
    direct_token = os.getenv("OAUTH_ACCESS_TOKEN") or os.getenv("GOOGLE_OAUTH_TOKEN")
    if direct_token and direct_token.strip():
        return direct_token.strip()

    refresh_token = os.getenv("USER_OAUTH_REFRESH_TOKEN")
    client_id = os.getenv("USER_OAUTH_CLIENT_ID")
    client_secret = os.getenv("USER_OAUTH_CLIENT_SECRET")
    if refresh_token and client_id and client_secret:
        try:
            creds = Credentials(
                token=None,
                refresh_token=refresh_token.strip(),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id.strip(),
                client_secret=client_secret.strip(),
            )
            creds.refresh(google.auth.transport.requests.Request())
            if creds.token:
                return creds.token
        except Exception as e:
            logger.warning("Failed to refresh user OAuth credentials: %s", e)
    return None


class DatastoreService:
    """Accesses connected Gemini Enterprise Data Stores and Federated Connectors.

    Direct implementation of the VeerMuchandi `ge_datastore_accessor_agent` blueprint
    extended for multi-connector IT Assistant use cases in Gemini Enterprise.
    """

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token
        self.creds = None
        if not self.access_token:
            self.access_token = _get_user_oauth_token()
        if not self.access_token:
            try:
                self.creds, _ = google.auth.default()
                auth_req = google.auth.transport.requests.Request()
                self.creds.refresh(auth_req)
                self.access_token = self.creds.token
            except Exception as e:
                logger.warning("Failed to get default credentials: %s", e)

    def _headers(self, project_id: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        }

    def _retry_with_user_oauth_if_unauthorized(
        self,
        response: requests.Response,
        method_url: str,
        project_id: str,
        payload: dict[str, Any],
    ) -> requests.Response:
        """If the initial token yields 401/403, retries once with refreshed user OAuth token."""
        if response.status_code in (401, 403):
            fallback_token = _get_user_oauth_token()
            if fallback_token and fallback_token != self.access_token:
                self.access_token = fallback_token
                return requests.post(
                    method_url,
                    headers=self._headers(project_id),
                    json=payload,
                    timeout=20,
                )
        return response

    def search_datastore(
        self,
        project_id: str,
        location: str,
        datastore_id: str,
        query: str,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """Searches a connected Discovery Engine Data Store via REST API."""
        endpoint_prefix = "" if location == "global" else f"{location}-"
        url = (
            f"https://{endpoint_prefix}discoveryengine.googleapis.com/v1alpha/"
            f"projects/{project_id}/locations/{location}/collections/default_collection/"
            f"dataStores/{datastore_id}/servingConfigs/default_search:search"
        )
        payload = {
            "query": query,
            "pageSize": page_size,
            "queryExpansionSpec": {"condition": "AUTO"},
            "spellCorrectionSpec": {"mode": "AUTO"},
        }
        response = requests.post(
            url, headers=self._headers(project_id), json=payload, timeout=20
        )
        response = self._retry_with_user_oauth_if_unauthorized(
            response, url, project_id, payload
        )
        response.raise_for_status()
        return response.json()

    def acquire_connector_token(
        self, project_id: str, location: str, collection_id: str
    ) -> str | None:
        """Acquires the stored 3P OAuth token from a Gemini Enterprise DataConnector."""
        endpoint_prefix = "" if location == "global" else f"{location}-"
        url = (
            f"https://{endpoint_prefix}discoveryengine.googleapis.com/v1alpha/"
            f"projects/{project_id}/locations/{location}/collections/{collection_id}/"
            f"dataConnector:acquireAccessToken"
        )
        response = requests.post(
            url, headers=self._headers(project_id), json={}, timeout=15
        )
        response = self._retry_with_user_oauth_if_unauthorized(
            response, url, project_id, {}
        )
        response.raise_for_status()
        return response.json().get("accessToken")


def _parse_discovery_results(
    raw_response: dict[str, Any], datastore_id: str
) -> list[dict[str, Any]]:
    """Normalizes Discovery Engine search results into clean structured records."""
    parsed: list[dict[str, Any]] = []
    for item in raw_response.get("results", []):
        doc = item.get("document", {})
        struct_data = doc.get("structData", {}) or {}
        derived_data = doc.get("derivedStructData", {}) or {}

        snippets = []
        for s in derived_data.get("snippets", []):
            if isinstance(s, dict) and s.get("snippet"):
                snippets.append(s["snippet"])
        for e in derived_data.get("extractive_answers", []):
            if isinstance(e, dict) and e.get("content"):
                snippets.append(e["content"])

        title = (
            struct_data.get("title")
            or derived_data.get("title")
            or struct_data.get("subject")
            or struct_data.get("summary")
            or doc.get("id", "Untitled")
        )
        link = (
            struct_data.get("url")
            or derived_data.get("link")
            or struct_data.get("html_url")
            or ""
        )
        record: dict[str, Any] = {
            "id": doc.get("id"),
            "datastore_id": datastore_id,
            "title": title,
            "url": link,
        }
        # Preserve key metadata fields for Calendar, Gmail, Drive, Jira, etc.
        for field in (
            "start_time",
            "end_time",
            "organizer",
            "attendees",
            "sender",
            "from",
            "to",
            "date",
            "status",
            "priority",
            "owner",
            "mime_type",
            "description",
            "text",
            "body",
        ):
            if struct_data.get(field):
                val = struct_data[field]
                if isinstance(val, str) and len(val) > 500:
                    val = val[:500] + "..."
                record[field] = val

        if snippets:
            record["snippets"] = snippets[:3]
        elif struct_data:
            # Provide a compact preview of struct_data if no snippets exist
            preview = {
                k: (v[:300] + "..." if isinstance(v, str) and len(v) > 300 else v)
                for k, v in list(struct_data.items())[:8]
            }
            record["metadata"] = preview

        parsed.append(record)
    return parsed


def _adf_to_text(node: Any) -> str:
    """Recursively extracts plain text from Atlassian Document Format (ADF) JSON."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        text_parts = []
        if "text" in node and isinstance(node["text"], str):
            text_parts.append(node["text"])
        for child in node.get("content", []):
            child_text = _adf_to_text(child)
            if child_text:
                text_parts.append(child_text)
        return " ".join(text_parts).strip()
    if isinstance(node, list):
        return " ".join(_adf_to_text(item) for item in node if item).strip()
    return ""


def search_datastore_records(
    query: str, tool_context: ToolContext | None = None
) -> dict[str, Any]:
    """Searches the primary connected Gemini Enterprise Data Store for relevant records.

    Follows the exact `search_datastore_records` signature and behavior from the
    `VeerMuchandi/Learn_ADK_Agents/ge_datastore_accessor_agent` blueprint.

    Args:
        query: The search query string to execute against the connected data store.
        tool_context: ADK ToolContext containing session state and OAuth tokens.

    Returns:
        A dictionary containing the status, source datastore, and matching records.
    """
    access_token = _extract_access_token(tool_context)
    project_id = _get_project_id()
    location = _get_location()
    datastore_id = os.getenv("DATA_STORE_ID") or DEFAULT_GDRIVE_DS

    try:
        service = DatastoreService(access_token)
        raw = service.search_datastore(project_id, location, datastore_id, query)
        records = _parse_discovery_results(raw, datastore_id)
        return {
            "status": "success",
            "app_id": os.getenv("GE_APP_ID") or DEFAULT_GE_APP_ID,
            "datastore_id": datastore_id,
            "query": query,
            "total_results": len(records),
            "results": records,
        }
    except Exception as e:
        logger.error("Error searching datastore %s: %s", datastore_id, e)
        return {
            "status": "error",
            "datastore_id": datastore_id,
            "query": query,
            "error_message": f"Failed to search datastore: {e!s}",
        }


def search_jira_tickets(
    query: str, project_key: str, tool_context: ToolContext | None = None
) -> dict[str, Any]:
    """Searches Jira tickets and IT issues connected to the Gemini Enterprise app.

    Queries the Jira Issue Data Store via `DatastoreService` and federates live
    against the connected Jira Cloud instance (project `SAM1`) to return real-time
    ticket statuses, priorities, issue types, and descriptions.

    Args:
        query: Ticket key (e.g., 'SAM1-23', 'SAM1-22'), keyword (e.g., 'GC5060', 'OAuth'),
            status ('To Do', 'In Progress', 'In Review', 'Done'), or 'all' to list tickets.
        project_key: The Jira project key to search in (use 'SAM1' for the default IT/Billing project).
        tool_context: ADK ToolContext containing session state and OAuth tokens.

    Returns:
        A dictionary with matching Jira tickets, statuses, priorities, and summaries.
    """
    access_token = _extract_access_token(tool_context)
    project_id = _get_project_id()
    location = _get_location()
    jira_ds = os.getenv("JIRA_DATA_STORE_ID") or DEFAULT_JIRA_DS
    jira_collection = os.getenv("JIRA_CONNECTOR_COLLECTION") or DEFAULT_JIRA_COLLECTION
    cloud_id = os.getenv("JIRA_CLOUD_ID") or DEFAULT_JIRA_CLOUD_ID
    effective_project = (
        project_key.strip().upper()
        if project_key and project_key.strip()
        else DEFAULT_JIRA_PROJECT
    )

    service = DatastoreService(access_token)
    datastore_records: list[dict[str, Any]] = []
    try:
        raw_ds = service.search_datastore(
            project_id, location, jira_ds, query, page_size=10
        )
        datastore_records = _parse_discovery_results(raw_ds, jira_ds)
    except Exception as e:
        logger.debug("Jira datastore search fallback: %s", e)

    federated_tickets: list[dict[str, Any]] = []
    try:
        jira_token = service.acquire_connector_token(
            project_id, location, jira_collection
        )
        if jira_token:
            jql = f"project={effective_project} ORDER BY created DESC"
            url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/search/jql"
            resp = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {jira_token}",
                    "Accept": "application/json",
                },
                params={
                    "jql": jql,
                    "maxResults": 25,
                    "fields": "summary,status,priority,issuetype,assignee,reporter,created,updated,description",
                },
                timeout=20,
            )
            resp.raise_for_status()
            issues = resp.json().get("issues", [])

            # Check if the query mentions a specific issue key like SAM1-23
            key_matches = re.findall(r"\b([A-Z][A-Z0-9]+-\d+)\b", query.upper())
            query_terms = [
                t.lower()
                for t in re.split(r"\W+", query)
                if len(t) > 2
                and t.lower()
                not in {
                    "what",
                    "the",
                    "latest",
                    "status",
                    "jira",
                    "ticket",
                    "tickets",
                    "issue",
                    "issues",
                    "for",
                    "and",
                    "are",
                    "open",
                    "project",
                    "all",
                    "show",
                    "list",
                    "find",
                    "check",
                }
            ]

            all_formatted: list[dict[str, Any]] = []
            matched_formatted: list[dict[str, Any]] = []

            for issue in issues:
                fields = issue.get("fields", {}) or {}
                key = issue.get("key", "")
                summary = fields.get("summary", "")
                status_name = (fields.get("status") or {}).get("name", "Unknown")
                priority_name = (fields.get("priority") or {}).get(
                    "name", "Unspecified"
                )
                issue_type = (fields.get("issuetype") or {}).get("name", "Task")
                assignee = (fields.get("assignee") or {}).get(
                    "displayName", "Unassigned"
                )
                desc_text = _adf_to_text(fields.get("description"))

                ticket_obj = {
                    "key": key,
                    "summary": summary,
                    "status": status_name,
                    "priority": priority_name,
                    "issue_type": issue_type,
                    "assignee": assignee,
                    "created": fields.get("created"),
                    "updated": fields.get("updated"),
                    "description": desc_text[:400] if desc_text else "",
                    "url": f"{os.getenv('JIRA_BROWSE_BASE_URL') or DEFAULT_JIRA_BROWSE_URL}/{key}",
                }
                all_formatted.append(ticket_obj)

                searchable_blob = (
                    f"{key} {summary} {status_name} {priority_name} {issue_type} {desc_text}"
                ).lower()
                if key in key_matches or any(
                    term in searchable_blob for term in query_terms
                ):
                    matched_formatted.append(ticket_obj)

            # Return both targeted matches and the full project board context so multi-part questions succeed
            federated_tickets = (
                all_formatted
                if not matched_formatted or len(all_formatted) <= 15
                else matched_formatted
            )
            return {
                "status": "success",
                "connector_id": jira_collection,
                "datastore_id": jira_ds,
                "project_key": effective_project,
                "query": query,
                "exact_matches_count": len(matched_formatted),
                "exact_matches": matched_formatted,
                "all_project_tickets": federated_tickets,
                "datastore_indexed_results": datastore_records,
            }
    except Exception as e:
        logger.error("Error querying federated Jira connector: %s", e)
        if datastore_records:
            return {
                "status": "success",
                "datastore_id": jira_ds,
                "query": query,
                "results": datastore_records,
            }
        return {
            "status": "error",
            "connector_id": jira_collection,
            "query": query,
            "error_message": f"Failed to query Jira tickets: {e!s}",
        }

    return {
        "status": "success",
        "datastore_id": jira_ds,
        "query": query,
        "results": datastore_records,
    }


def search_it_knowledge_base(
    query: str, tool_context: ToolContext | None = None
) -> dict[str, Any]:
    """Searches connected Google Drive and NotebookLM data stores for IT runbooks, resolution plans, and security docs.

    Queries the configured Google Drive and NotebookLM data stores in Gemini Enterprise
    using `DatastoreService`.

    Args:
        query: Search query for IT runbooks, resolution plans (e.g., 'GC5060'),
            security questionnaires, or architecture documents.
        tool_context: ADK ToolContext containing session state and OAuth tokens.

    Returns:
        A dictionary containing matching Google Drive documents and Notebook records.
    """
    access_token = _extract_access_token(tool_context)
    project_id = _get_project_id()
    location = _get_location()
    gdrive_ds = os.getenv("GDRIVE_DATA_STORE_ID") or DEFAULT_GDRIVE_DS
    gnotebook_ds = os.getenv("GNOTEBOOK_DATA_STORE_ID") or DEFAULT_GNOTEBOOK_DS

    service = DatastoreService(access_token)
    combined_results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    errors: list[str] = []

    sub_queries = [query]
    # Also extract short uppercase/alphanumeric product or project codes (e.g. GC5060)
    code_tokens = re.findall(r"\b[A-Z]{2,}\d{2,}\b", query)
    for token in code_tokens:
        if token != query and token not in sub_queries:
            sub_queries.append(token)

    for ds_id in (gdrive_ds, gnotebook_ds):
        for sub_q in sub_queries:
            try:
                raw = service.search_datastore(
                    project_id, location, ds_id, sub_q, page_size=12
                )
                for item in _parse_discovery_results(raw, ds_id):
                    item_id = str(item.get("id") or item.get("title"))
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        combined_results.append(item)
            except Exception as e:
                errors.append(f"{ds_id} ({sub_q}): {e!s}")

    return {
        "status": "success" if combined_results or not errors else "error",
        "query": query,
        "datastores_searched": [gdrive_ds, gnotebook_ds],
        "total_results": len(combined_results),
        "results": combined_results,
        "warnings": errors if errors else None,
    }


def search_it_emails_and_calendar(
    query: str, source_type: str, tool_context: ToolContext | None = None
) -> dict[str, Any]:
    """Searches connected Gmail and Google Calendar data stores for IT notifications, security alerts, and onboarding schedules.

    Queries the configured Gmail and/or Google Calendar data stores in Gemini Enterprise
    using `DatastoreService`.

    Args:
        query: Search keywords (e.g., 'IT Laptop Setup', '30-Day Check-in', 'Salesforce security token', 'SAM1-9').
        source_type: Which connected Workspace datastore to search: 'gmail', 'calendar', or 'both'.
        tool_context: ADK ToolContext containing session state and OAuth tokens.

    Returns:
        A dictionary containing matching Gmail messages and/or Google Calendar events.
    """
    access_token = _extract_access_token(tool_context)
    project_id = _get_project_id()
    location = _get_location()
    gmail_ds = os.getenv("GMAIL_DATA_STORE_ID") or DEFAULT_GMAIL_DS
    gcal_ds = os.getenv("GCAL_DATA_STORE_ID") or DEFAULT_GCAL_DS

    normalized_source = (source_type or "both").strip().lower()
    target_stores: list[str] = []
    if normalized_source in ("gmail", "mail", "email", "emails"):
        target_stores = [gmail_ds]
    elif normalized_source in ("calendar", "gcal", "events", "schedule"):
        target_stores = [gcal_ds]
    else:
        target_stores = [gmail_ds, gcal_ds]

    service = DatastoreService(access_token)
    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    errors: list[str] = []

    # Split compound boolean queries ("A or B", "A and B") so Discovery Engine
    # matches each distinct event or email topic reliably.
    sub_queries = [
        q.strip()
        for q in re.split(r"\b(?:OR|or|AND|and)\b|,|;", query)
        if q.strip() and len(q.strip()) > 2
    ]
    if not sub_queries:
        sub_queries = [query]
    elif len(sub_queries) > 1 and query not in sub_queries:
        sub_queries.append(query)

    for ds_id in target_stores:
        for sub_q in sub_queries:
            try:
                raw = service.search_datastore(
                    project_id, location, ds_id, sub_q, page_size=10
                )
                for item in _parse_discovery_results(raw, ds_id):
                    item_id = str(item.get("id") or item.get("title"))
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        results.append(item)
            except Exception as e:
                errors.append(f"{ds_id} ({sub_q}): {e!s}")

    return {
        "status": "success" if results or not errors else "error",
        "query": query,
        "source_type": normalized_source,
        "datastores_searched": target_stores,
        "total_results": len(results),
        "results": results,
        "warnings": errors if errors else None,
    }


def search_salesforce_cases(
    query: str, tool_context: ToolContext | None = None
) -> dict[str, Any]:
    """Searches connected Salesforce support cases and escalations in Gemini Enterprise.

    Queries the Salesforce Case Data Store and federates against the connected
    Salesforce org for live support cases (e.g., Case `00001002` regarding `GC5060` electrical wiring).

    Args:
        query: Case number (e.g., '00001002'), product/topic (e.g., 'GC5060', 'generator', 'electrical'),
            or 'all' to list open and recent support cases.
        tool_context: ADK ToolContext containing session state and OAuth tokens.

    Returns:
        A dictionary containing matching Salesforce Case records with CaseNumber, Subject, Status, Priority, and Description.
    """
    access_token = _extract_access_token(tool_context)
    project_id = _get_project_id()
    location = _get_location()
    sf_case_ds = os.getenv("SF_CASE_DATA_STORE_ID") or DEFAULT_SF_CASE_DS
    sf_collection = os.getenv("SF_CONNECTOR_COLLECTION") or DEFAULT_SF_COLLECTION
    sf_instance = os.getenv("SF_INSTANCE_URL") or DEFAULT_SF_INSTANCE_URL

    service = DatastoreService(access_token)
    datastore_records: list[dict[str, Any]] = []
    try:
        raw_ds = service.search_datastore(
            project_id, location, sf_case_ds, query, page_size=10
        )
        datastore_records = _parse_discovery_results(raw_ds, sf_case_ds)
    except Exception as e:
        logger.debug("Salesforce datastore search fallback: %s", e)

    try:
        sf_token = service.acquire_connector_token(project_id, location, sf_collection)
        if sf_token:
            soql = (
                "SELECT Id, CaseNumber, Subject, Status, Priority, Origin, "
                "Description, CreatedDate FROM Case ORDER BY CreatedDate DESC LIMIT 20"
            )
            resp = requests.get(
                f"{sf_instance}/services/data/v60.0/query",
                headers={"Authorization": f"Bearer {sf_token}"},
                params={"q": soql},
                timeout=20,
            )
            resp.raise_for_status()
            raw_cases = resp.json().get("records", [])

            query_terms = [
                t.lower()
                for t in re.split(r"\W+", query)
                if len(t) > 2
                and t.lower()
                not in {
                    "what",
                    "the",
                    "status",
                    "case",
                    "cases",
                    "salesforce",
                    "support",
                    "open",
                    "all",
                    "check",
                    "find",
                }
            ]

            all_cases: list[dict[str, Any]] = []
            matched_cases: list[dict[str, Any]] = []
            for rec in raw_cases:
                case_obj = {
                    "id": rec.get("Id"),
                    "case_number": rec.get("CaseNumber"),
                    "subject": rec.get("Subject"),
                    "status": rec.get("Status"),
                    "priority": rec.get("Priority"),
                    "origin": rec.get("Origin"),
                    "description": rec.get("Description") or "",
                    "created_date": rec.get("CreatedDate"),
                }
                all_cases.append(case_obj)
                blob = (
                    f"{case_obj['case_number']} {case_obj['subject']} "
                    f"{case_obj['status']} {case_obj['priority']} {case_obj['description']}"
                ).lower()
                if any(term in blob for term in query_terms):
                    matched_cases.append(case_obj)

            return {
                "status": "success",
                "connector_id": sf_collection,
                "datastore_id": sf_case_ds,
                "query": query,
                "exact_matches_count": len(matched_cases),
                "exact_matches": matched_cases,
                "recent_cases": all_cases[:10],
                "datastore_indexed_results": datastore_records,
            }
    except Exception as e:
        logger.error("Error querying Salesforce connector: %s", e)
        return {
            "status": "error",
            "connector_id": sf_collection,
            "query": query,
            "error_message": f"Failed to query Salesforce cases: {e!s}",
        }

    return {
        "status": "success",
        "datastore_id": sf_case_ds,
        "query": query,
        "results": datastore_records,
    }


def search_github_engineering(
    query: str, resource_type: str, tool_context: ToolContext | None = None
) -> dict[str, Any]:
    """Searches connected GitHub repositories and issues in Gemini Enterprise.

    Queries the GitHub Data Stores via `DatastoreService` and federates live
    against the connected GitHub account.

    Args:
        query: Search keywords (e.g., 'adk-salesforce-agent', 'spark', 'daily status', 'a2ui').
        resource_type: Type of GitHub resource to search: 'repositories', 'issues', or 'both'.
        tool_context: ADK ToolContext containing session state and OAuth tokens.

    Returns:
        A dictionary containing matching GitHub repositories and/or issues.
    """
    access_token = _extract_access_token(tool_context)
    project_id = _get_project_id()
    location = _get_location()
    gh_issue_ds = os.getenv("GITHUB_ISSUE_DATA_STORE_ID") or DEFAULT_GH_ISSUE_DS
    gh_repo_ds = os.getenv("GITHUB_REPO_DATA_STORE_ID") or DEFAULT_GH_REPO_DS
    gh_collection = os.getenv("GITHUB_CONNECTOR_COLLECTION") or DEFAULT_GH_COLLECTION

    service = DatastoreService(access_token)
    datastore_records: list[dict[str, Any]] = []
    for ds_id in (gh_repo_ds, gh_issue_ds):
        try:
            raw_ds = service.search_datastore(
                project_id, location, ds_id, query, page_size=8
            )
            datastore_records.extend(_parse_discovery_results(raw_ds, ds_id))
        except Exception as e:
            logger.debug("GitHub datastore %s search fallback: %s", ds_id, e)

    repos_out: list[dict[str, Any]] = []
    try:
        gh_token = service.acquire_connector_token(project_id, location, gh_collection)
        if gh_token:
            gh_headers = {
                "Authorization": f"Bearer {gh_token}",
                "Accept": "application/vnd.github+json",
            }
            resp = requests.get(
                "https://api.github.com/user/repos",
                headers=gh_headers,
                params={
                    "affiliation": "owner",
                    "per_page": 25,
                    "sort": "updated",
                },
                timeout=20,
            )
            resp.raise_for_status()
            for r in resp.json():
                repos_out.append(
                    {
                        "full_name": r.get("full_name"),
                        "name": r.get("name"),
                        "description": r.get("description") or "",
                        "html_url": r.get("html_url"),
                        "language": r.get("language"),
                        "updated_at": r.get("updated_at"),
                        "open_issues_count": r.get("open_issues_count", 0),
                    }
                )
    except Exception as e:
        logger.warning("GitHub federated repo lookup warning: %s", e)

    return {
        "status": "success",
        "connector_id": gh_collection,
        "datastores_searched": [gh_repo_ds, gh_issue_ds],
        "query": query,
        "resource_type": resource_type,
        "repositories": repos_out,
        "datastore_results": datastore_records,
    }
