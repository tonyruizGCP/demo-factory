"""Authentication configuration for OAuth 2.0 with Google APIs.

Follows the pattern from:
https://fmind.medium.com/powering-up-your-agent-in-production-with-adk-oauth-and-gemini-enterprise-a52b0716fcba

In local dev (ADK Web UI): AUTH_CONFIG is used by the ADK OAuth flow
to prompt the user for consent and exchange the auth code for tokens.

In production (Agent Engine + Gemini Enterprise): The token is injected
by Gemini Enterprise into tool_context.state — AUTH_CONFIG is not used,
but TOKEN_CACHE_KEY and SCOPES are still referenced by negotiate_creds().
"""

import os
from fastapi.openapi.models import (
    OAuth2,
    OAuthFlowAuthorizationCode,
    OAuthFlows,
)

try:
    from google.adk.auth.auth_credential import (
        AuthCredential,
        AuthCredentialTypes,
        OAuth2Auth,
    )
    from google.adk.auth.auth_tool import AuthConfig
except ImportError:
    class AuthCredentialTypes:
        OAUTH2 = "OAUTH2"
    class OAuth2Auth:
        def __init__(self, client_id="", client_secret=""):
            self.client_id = client_id
            self.client_secret = client_secret
    class AuthCredential:
        def __init__(self, auth_type=None, oauth2=None):
            self.auth_type = auth_type
            self.oauth2 = oauth2
    class AuthConfig:
        def __init__(self, auth_scheme=None, raw_auth_credential=None):
            self.auth_scheme = auth_scheme
            self.raw_auth_credential = raw_auth_credential

# --- OAuth 2.0 Endpoints ---
AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# --- Scopes ---
SCOPES = {
    "https://www.googleapis.com/auth/drive.readonly": "Google Drive API (read-only)",
}

# --- Token cache key ---
TOKEN_CACHE_KEY = os.environ.get("AUTH_ID", "google-drive-auth")

# --- OAuth scheme + credential ---
AUTH_SCHEME = OAuth2(
    flows=OAuthFlows(
        authorizationCode=OAuthFlowAuthorizationCode(
            authorizationUrl=AUTHORIZATION_URL,
            tokenUrl=TOKEN_URL,
            scopes=SCOPES,
        )
    )
)

AUTH_CREDENTIAL = AuthCredential(
    auth_type=AuthCredentialTypes.OAUTH2,
    oauth2=OAuth2Auth(
        client_id=os.environ.get("OAUTH_CLIENT_ID", ""),
        client_secret=os.environ.get("OAUTH_CLIENT_SECRET", ""),
    ),
)

AUTH_CONFIG = AuthConfig(
    auth_scheme=AUTH_SCHEME,
    raw_auth_credential=AUTH_CREDENTIAL,
)
