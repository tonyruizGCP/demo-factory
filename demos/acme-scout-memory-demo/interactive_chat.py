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

"""GECX Acme Scout with Memory Interactive Chat Client

PURPOSE:
    Launches an interactive terminal chat session with the Acme Scout with Memory Agent.
    Demonstrates cross-session retrieval and persistence of enterprise infrastructure
    preferences, architectural constraints, and procurement requirements using Vertex AI Memory Bank.
"""

import os
import sys

# Add root directory to path to ensure imports resolve correctly
sys.path.insert(0, os.getcwd())

try:
    from cxas_scrapi.core.sessions import Sessions
except ImportError:
    print("ERROR: cxas-scrapi is not installed in this environment.")
    print("Please activate the virtualenv first (source .venv/bin/activate).")
    sys.exit(1)


def main():
    print("==================================================================")
    print(" 🚀 Acme Corp Solutions Scout with Vertex Memory Terminal Client")
    print("==================================================================")

    # Get App ID from environment or arguments
    app_id = os.environ.get("CXAS_APP_ID")
    if not app_id:
        if len(sys.argv) > 1:
            app_id = sys.argv[1]
        else:
            print("ERROR: GECX App ID or Resource Name is required.")
            print("Usage: python interactive_chat.py [YOUR_APP_ID]")
            print("Or set the CXAS_APP_ID environment variable.")
            sys.exit(1)

    # Ensure it is a full resource path
    if not app_id.startswith("projects/"):
        project = os.environ.get("GCP_PROJECT")
        if not project:
            project = "truiz-cx-agent-studio"
        
        app_resource = f"projects/{project}/locations/us/apps/{app_id}"
    else:
        app_resource = app_id

    print(f"Connecting to deployed Acme GECX Agent:\n  {app_resource}")

    # 1. Initialize the Sessions client
    try:
        session_client = Sessions(app_resource)
    except Exception as e:
        print(f"Failed to connect to GECX Sessions: {e}")
        sys.exit(1)

    # 2. Prompt for Enterprise User ID (demonstrating tenant/user memory isolation)
    print("\nEnter your Enterprise User ID / Email (e.g. 'alice@acme.com' or 'tonyruiz'):")
    user_id = input("Enter User ID: ").strip()
    if not user_id:
        user_id = "default_acme_engineer"
        print(f"No ID entered, using default: '{user_id}'")

    session_id = session_client.create_session_id()

    print(f"\nSession established for User ID: '{user_id}'")
    print("Type 'exit' or 'quit' to conclude the session.")
    print("Start by saying 'Hi' or inquiring about hardware/cloud solutions.")
    print("------------------------------------------------------------------")

    is_first_turn = True

    while True:
        try:
            user_input = input("\nYou: ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting session. Goodbye!")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Concluding Acme Scout session. Have a productive day!")
            break

        # Prepare turn parameters
        kwargs = {
            "session_id": session_id,
            "text": user_input,
            "modality": "text"
        }

        # On the very first turn, inject the user_id variable
        if is_first_turn:
            kwargs["variables"] = {
                "user_id": user_id
            }
            is_first_turn = False

        # Execute the conversational turn
        try:
            response = session_client.run(**kwargs)
            session_client.parse_result(response)
        except Exception as e:
            print(f"\nError during conversational turn: {e}")
            break


if __name__ == "__main__":
    main()
