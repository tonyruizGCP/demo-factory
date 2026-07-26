import os
import sys
import getpass
import urllib.parse
import requests

try:
    import google.auth
    from google.auth.transport.requests import Request
except ImportError:
    google = None

def get_config(var_name, prompt, default=None, is_secret=False):
    """Helper to get config from env or user input."""
    value = os.environ.get(var_name)
    if not value:
        full_prompt = f"{prompt} [{default}]: " if default else f"{prompt}: "
        if is_secret:
            value = getpass.getpass(prompt + ": ")
        else:
            value = input(full_prompt).strip() or default
    return value

def register_oauth():
    print("--- [ Interactive Gemini Enterprise OAuth Registration ] ---")
    
    project_id = get_config("GCP_PROJECT", "Enter Google Cloud Project ID") or get_config("GOOGLE_CLOUD_PROJECT", "Enter Google Cloud Project ID")
    location = get_config("LOCATION", "Enter Location (global/eu/us)", default="global")
    endpoint_location = os.environ.get("ENDPOINT_LOCATION", "eu" if location == "eu" else "global")
    
    auth_id = get_config("AUTH_ID", "Enter Authorization ID", default="google-drive-auth")
    client_id = get_config("OAUTH_CLIENT_ID", "Enter OAuth Client ID")
    client_secret = get_config("OAUTH_CLIENT_SECRET", "Enter OAuth Client Secret", is_secret=True)
    
    token_uri = os.environ.get("OAUTH_TOKEN_URI", "https://oauth2.googleapis.com/token")
    default_scopes = "https://www.googleapis.com/auth/drive.readonly"
    scopes = get_config("OAUTH_SCOPES", "Enter OAuth Scopes (space-separated)", default=default_scopes)

    if not all([project_id, auth_id, client_id, client_secret]):
        print("❌ Error: Missing required configuration details.")
        sys.exit(1)

    if google is None:
        print("❌ Error: google-auth is not installed.")
        sys.exit(1)

    try:
        credentials, _ = google.auth.default()
        if not credentials.valid:
            credentials.refresh(Request())
        access_token = credentials.token
    except Exception as e:
        print(f"❌ Error getting Google Auth token: {e}")
        sys.exit(1)

    base_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": client_id,
        "redirect_uri": "https://vertexaisearch.cloud.google.com/oauth-redirect",
        "scope": scopes,
        "include_granted_scopes": "true",
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_uri = f"{base_auth_url}?{urllib.parse.urlencode(params)}"

    base_url = f"https://{endpoint_location}-discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/authorizations"
    resource_name = f"projects/{project_id}/locations/{location}/authorizations/{auth_id}"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id
    }

    payload = {
        "name": resource_name,
        "serverSideOauth2": {
            "clientId": client_id,
            "clientSecret": client_secret,
            "authorizationUri": auth_uri,
            "tokenUri": token_uri
        }
    }

    print(f"\nRegistering Authorization resource '{auth_id}' in {location}...")
    
    try:
        response = requests.post(f"{base_url}?authorizationId={auth_id}", headers=headers, json=payload)
        
        if response.status_code == 200:
            print("✅ Successfully registered authorization resource.")
            print(response.json())
        elif response.status_code == 409:
            print(f"⚠️  Authorization resource '{auth_id}' already exists. Recreating...")
            del_response = requests.delete(f"{base_url}/{auth_id}", headers=headers)
            if del_response.status_code in [200, 204]:
                retry_response = requests.post(f"{base_url}?authorizationId={auth_id}", headers=headers, json=payload)
                if retry_response.status_code == 200:
                    print("✅ Successfully re-registered authorization resource.")
                    print(retry_response.json())
                else:
                    print(f"❌ Failed to recreate. Status: {retry_response.status_code}")
                    print(retry_response.text)
            else:
                print(f"❌ Failed to delete existing resource. Status: {del_response.status_code}")
        else:
            print(f"❌ Failed to register. Status: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    register_oauth()
