# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for the Enterprise IT Assistant (`DatastoreService`, tools, and ADK 2.0 agent)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.agent import EXECUTION_BUDGET_CONFIG, app, root_agent
from app.tools import (
    DatastoreService,
    _adf_to_text,
    _extract_access_token,
    _parse_discovery_results,
    search_datastore_records,
)


def test_app_and_root_agent_structure() -> None:
    """Verifies that the ADK 2.0 `app` and `root_agent` are properly configured with execution budgets."""
    assert app.name == "app"
    assert app.root_agent.name == "root_agent"
    assert root_agent.generate_content_config == EXECUTION_BUDGET_CONFIG
    assert EXECUTION_BUDGET_CONFIG.max_output_tokens == 2048
    sub_agent_names = [sa.name for sa in root_agent.sub_agents]
    assert "jira_ticket_specialist" in sub_agent_names
    assert "workspace_it_specialist" in sub_agent_names
    assert "devops_crm_specialist" in sub_agent_names


def test_extract_access_token_from_tool_context() -> None:
    """Verifies 3LO OAuth token extraction from `tool_context.state` (both direct and temp: keys)."""
    mock_ctx = SimpleNamespace(
        state={"it_assistant_oauth_token": "mock_token_mock_ge_user_token_1234567890"}
    )
    assert (
        _extract_access_token(mock_ctx)  # type: ignore[arg-type]
        == "mock_token_mock_ge_user_token_1234567890"
    )
    temp_ctx = SimpleNamespace(
        state={"temp:it_assistant_oauth_token": "mock_token_temp_ge_user_token_1234567890"}
    )
    assert (
        _extract_access_token(temp_ctx)  # type: ignore[arg-type]
        == "mock_token_temp_ge_user_token_1234567890"
    )
    assert _extract_access_token(None) is None


def test_adf_to_text_conversion() -> None:
    """Verifies Atlassian Document Format (ADF) JSON parsing into plain text."""
    adf_doc = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "GC5060 wiring escalation"},
                    {"type": "text", "text": "requires immediate review."},
                ],
            }
        ],
    }
    assert (
        _adf_to_text(adf_doc) == "GC5060 wiring escalation requires immediate review."
    )


def test_parse_discovery_results() -> None:
    """Verifies normalization of Discovery Engine search response payloads."""
    raw = {
        "results": [
            {
                "document": {
                    "id": "doc-123",
                    "structData": {
                        "title": "GC5060 Pipeline Resolution Plan",
                        "url": "https://docs.google.com/document/d/doc-123",
                        "owner": "Acme Co. IT Engineering",
                    },
                    "derivedStructData": {
                        "snippets": [{"snippet": "Step 1: Inspect generator harness."}]
                    },
                }
            }
        ]
    }
    parsed = _parse_discovery_results(raw, "acme-gdrive-ds_google_drive")
    assert len(parsed) == 1
    assert parsed[0]["id"] == "doc-123"
    assert parsed[0]["title"] == "GC5060 Pipeline Resolution Plan"
    assert parsed[0]["snippets"] == ["Step 1: Inspect generator harness."]


@patch("app.tools.requests.post")
def test_datastore_service_with_explicit_token(mock_post: MagicMock) -> None:
    """Verifies that DatastoreService uses the provided OAuth token without calling ADC."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": []}
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    svc = DatastoreService(access_token="mock_token_explicit_token")
    res = svc.search_datastore(
        "acme-enterprise-demo",
        "global",
        "acme-gdrive-ds_google_drive",
        "GC5060",
    )
    assert res == {"results": []}
    called_headers = mock_post.call_args.kwargs["headers"]
    assert called_headers["Authorization"] == "Bearer mock_token_explicit_token"
    assert called_headers["X-Goog-User-Project"] == "acme-enterprise-demo"


@patch("app.tools.DatastoreService.search_datastore")
def test_search_datastore_records_blueprint_tool(
    mock_search: MagicMock,
) -> None:
    """Verifies the blueprint `search_datastore_records` tool function."""
    mock_search.return_value = {
        "results": [
            {
                "document": {
                    "id": "1eKtqmFu",
                    "structData": {"title": "GC5060 Pipeline Resolution Plan"},
                }
            }
        ]
    }
    mock_ctx = SimpleNamespace(
        state={"it_assistant_oauth_token": "mock_token_test_token_value_1234567890"}
    )
    out = search_datastore_records("GC5060", mock_ctx)  # type: ignore[arg-type]
    assert out["status"] == "success"
    assert out["total_results"] == 1
    assert out["results"][0]["title"] == "GC5060 Pipeline Resolution Plan"
