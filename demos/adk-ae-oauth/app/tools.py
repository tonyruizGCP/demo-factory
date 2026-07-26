"""Tools for the Google Drive reader agent.

Implements the OAuth credential negotiation pattern from:
https://fmind.medium.com/powering-up-your-agent-in-production-with-adk-oauth-and-gemini-enterprise-a52b0716fcba
"""

import json
import logging
from typing import Any, Dict, Union

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

try:
    from google.adk.tools import ToolContext
except ImportError:
    class ToolContext:
        def __init__(self, state=None):
            self.state = state if state is not None else {}
        def get_auth_response(self, auth_config):
            return None
        def request_credential(self, auth_config):
            pass

try:
    from googleapiclient.discovery import build
except ImportError:
    build = None

from app import auths

logger = logging.getLogger(__name__)


def negotiate_creds(tool_context: ToolContext) -> Union[Credentials, dict]:
    """Handle the OAuth 2.0 flow to get valid credentials.

    This function implements a three-stage credential resolution:
    1. Check for cached credentials in tool_context.state (including tokens
       injected by Gemini Enterprise via "temp:<AUTH_ID>").
    2. Check for an auth response from the ADK OAuth flow.
    3. If nothing is available, initiate the OAuth flow.
    """
    logger.info("Negotiating credentials using OAuth 2.0")

    # --- Stage 1: Check for cached / injected token ---
    cached_token = tool_context.state.get(auths.TOKEN_CACHE_KEY)

    if cached_token is None:
        cached_token = tool_context.state.get(f"temp:{auths.TOKEN_CACHE_KEY}")

    if cached_token:
        logger.debug("Found cached token in tool context state")

        if isinstance(cached_token, dict):
            try:
                creds = Credentials.from_authorized_user_info(
                    cached_token, list(auths.SCOPES.keys())
                )
                if creds.valid:
                    return creds
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    tool_context.state[auths.TOKEN_CACHE_KEY] = json.loads(
                        creds.to_json()
                    )
                    return creds
            except Exception as error:
                logger.error(f"Error loading/refreshing cached credentials: {error}")
                tool_context.state[auths.TOKEN_CACHE_KEY] = None

        elif isinstance(cached_token, str):
            return Credentials(token=cached_token)
        else:
            raise ValueError(
                f"Invalid cached token type. Expected dict or str, got {type(cached_token)}"
            )

    # --- Stage 2: Check for an auth response from the ADK OAuth flow ---
    if hasattr(tool_context, "get_auth_response"):
        if exchanged_creds := tool_context.get_auth_response(auths.AUTH_CONFIG):
            auth_scheme = auths.AUTH_CONFIG.auth_scheme
            auth_credential = auths.AUTH_CONFIG.raw_auth_credential
            creds = Credentials(
                token=exchanged_creds.oauth2.access_token,
                refresh_token=exchanged_creds.oauth2.refresh_token,
                token_uri=auth_scheme.flows.authorizationCode.tokenUrl,
                client_id=auth_credential.oauth2.client_id,
                client_secret=auth_credential.oauth2.client_secret,
                scopes=list(auth_scheme.flows.authorizationCode.scopes.keys()),
            )
            tool_context.state[auths.TOKEN_CACHE_KEY] = json.loads(creds.to_json())
            return creds

    # --- Stage 3: Initiate OAuth flow ---
    if hasattr(tool_context, "request_credential"):
        tool_context.request_credential(auths.AUTH_CONFIG)

    return {"pending": True, "message": "Awaiting user OAuth authentication"}


def read_drive_file(file_id: str, tool_context: ToolContext) -> dict:
    """Read the text content of a Google Drive file.

    Args:
        file_id: The Google Drive file ID to read.

    Returns:
        A dict with 'status' and 'content' keys.
    """
    creds = negotiate_creds(tool_context)

    if isinstance(creds, dict):
        return creds

    if build is None:
        return {"status": "error", "message": "googleapiclient is not installed"}

    try:
        service = build("drive", "v3", credentials=creds)

        file_meta = (
            service.files()
            .get(fileId=file_id, fields="id,name,mimeType")
            .execute()
        )
        file_name = file_meta.get("name", "unknown")
        mime_type = file_meta.get("mimeType", "")

        if mime_type in [
            "application/vnd.google-apps.document",
            "application/vnd.google-apps.spreadsheet",
            "application/vnd.google-apps.presentation",
        ]:
            export_type = "text/plain" if mime_type != "application/vnd.google-apps.spreadsheet" else "text/csv"
            content = service.files().export(fileId=file_id, mimeType=export_type).execute()
        else:
            content = service.files().get_media(fileId=file_id).execute()

        text_content = content.decode("utf-8") if isinstance(content, bytes) else content

        return {
            "status": "success",
            "file_name": file_name,
            "mime_type": mime_type,
            "content": text_content,
        }

    except Exception as e:
        logger.error(f"Error reading Drive file: {e}")
        return {
            "status": "error",
            "message": f"Failed to read file: {str(e)}",
        }
