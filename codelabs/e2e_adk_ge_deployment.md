# End-to-End Customer Guide: Build, Evaluate, Deploy, and Publish an Agent with Agents CLI (`v1.11.0+`)

This guide provides the updated, copy-paste-ready "happy path" instructions for the [Agents CLI in Agent Platform Codelab](https://codelabs.developers.google.com/agents-cli-agent-platform/agents-cli-agent-platform#0) using **`agents-cli v1.11.0+`**.

---

## Step 1: Install & Verify Prerequisite Tools

Run the commands below for your operating system to install and verify all required dependencies (`uv`, **Python 3.11+**, **Node.js 18+**, **`jq`**, and the **Google Cloud SDK (`gcloud`)**).

### 1. Install `uv` and Python 3.11+
```bash
# Install uv (macOS / Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Ensure ~/.local/bin is on your PATH
export PATH="$HOME/.local/bin:$PATH"

# Install Python 3.11 via uv (if not already installed)
uv python install 3.11

# Verify uv and Python
uv --version
uv python find 3.11
```

### 2. Install Node.js 18+ and `jq`
* **macOS (Homebrew):**
  ```bash
  brew install node jq
  ```
* **Linux (Debian / Ubuntu):**
  ```bash
  sudo apt-get update && sudo apt-get install -y nodejs npm jq
  ```
* **Verify:**
  ```bash
  node --version   # Must be v18+
  npx --version
  jq --version
  ```

### 3. Install the Google Cloud SDK (`gcloud`)
* **macOS (Homebrew):**
  ```bash
  brew install --cask google-cloud-sdk
  ```
* **Linux / macOS (Official Installer Script):**
  ```bash
  curl https://sdk.cloud.google.com | bash
  exec -l $SHELL
  ```
* **Verify:**
  ```bash
  gcloud --version
  ```

---

## Step 2: Before You Begin (Google Cloud Setup)

Set your project and region environment variables, configure `gcloud`, enable the required Google Cloud APIs, and authenticate:

```bash
# 1. Set your Google Cloud Project ID and default region
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="us-central1"

# 2. Configure gcloud to use your project
gcloud config set project "$GOOGLE_CLOUD_PROJECT"

# 3. Enable required Google Cloud APIs (including Discovery Engine for Gemini Enterprise publishing)
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudtrace.googleapis.com \
  cloudbuild.googleapis.com \
  discoveryengine.googleapis.com \
  --project="$GOOGLE_CLOUD_PROJECT"

# 4. Authenticate user and Application Default Credentials (ADC)
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project "$GOOGLE_CLOUD_PROJECT"
```

---

## Step 3: Install (or Upgrade) Agents CLI

### Option A: With a Coding Agent (Antigravity, Gemini CLI, Claude Code, Cursor)
```bash
uvx google-agents-cli setup
```
*(If you already installed `google-agents-cli` previously, upgrade both the CLI and the installed coding-agent skills:)*
```bash
uv tool install --reinstall google-agents-cli
agents-cli update
```

### Option B: Manual Mode (CLI Only)
```bash
uv tool install --reinstall google-agents-cli
```

Verify your installed version (`1.11.0` or newer):
```bash
agents-cli --version
```

---

## Step 4: Create Your Agent Project

### 🤖 With a Coding Agent
> *"Create a new ADK agent project called `customer-support-agent` using the prototype template."*

### 👤 Manual Mode
```bash
agents-cli scaffold create customer-support-agent --prototype --yes
```

Move into the newly created project directory:
```bash
cd customer-support-agent
```

---

## Step 5: Explore the Agent Code & Environment Configuration

Inspect the generated files without overwriting them:
* **`app/agent.py`** — Defines `get_weather`, `get_current_time`, and `root_agent = Agent(name="customer_support_agent", ...)`.
* **`.env`** — Stores runtime environment variables for local execution.

Verify that `.env` contains your project ID and points to Vertex AI:
```bash
cat .env
```
Expected `.env` contents:
```dotenv
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=global
```

---

## Step 6: Test Locally with the Playground

### 🤖 With a Coding Agent
> *"Install dependencies and start the local playground for my agent."*

### 👤 Manual Mode
1. Install the project dependencies into `.venv`:
   ```bash
   agents-cli install
   ```
2. Launch the interactive web playground:
   ```bash
   agents-cli playground
   ```
3. Open `http://127.0.0.1:8080/dev-ui/?app=app` in your browser and test prompts such as:
   * `"What's the weather in San Francisco?"`
   * `"What's the weather in Tokyo?"`
   * `"What time is it in San Francisco?"`

Press `Ctrl+C` in the terminal when finished to stop the playground server.

---

## Step 7: Run from the Command Line

Test your agent non-interactively from your terminal:

### 🤖 With a Coding Agent
> *"Run the agent with the query 'What's the weather in San Francisco?'"*

### 👤 Manual Mode
```bash
agents-cli run "What's the weather in San Francisco?"
```

When finished testing locally, you can stop the warm background server at any time with:
```bash
agents-cli run --stop-server
```

---

## Step 8: Evaluate Your Agent

Evaluations in `agents-cli v1.11.0+` use two files in `tests/eval/`:
1. **`tests/eval/datasets/basic-dataset.json`** — The evaluation test cases (`prompt`, `reference`, and `expected_tool_calls`).
2. **`tests/eval/eval_config.yaml`** — The metrics configuration (`metrics_to_run` and `custom_metrics`).

### 1. Update the Evaluation Dataset (`tests/eval/datasets/basic-dataset.json`)
Replace the contents of `tests/eval/datasets/basic-dataset.json` with:

```bash
cat << 'EOF' > tests/eval/datasets/basic-dataset.json
{
  "eval_cases": [
    {
      "eval_case_id": "weather_san_francisco",
      "prompt": {
        "role": "user",
        "parts": [
          {
            "text": "What's the weather like in San Francisco?"
          }
        ]
      },
      "reference": {
        "response": {
          "role": "model",
          "parts": [
            {
              "text": "The weather in San Francisco is 60 degrees and foggy."
            }
          ]
        }
      },
      "expected_tool_calls": [
        {
          "name": "get_weather",
          "args": {
            "query": "San Francisco"
          }
        }
      ]
    },
    {
      "eval_case_id": "time_new_york",
      "prompt": {
        "role": "user",
        "parts": [
          {
            "text": "What's the current time in New York?"
          }
        ]
      },
      "reference": {
        "response": {
          "role": "model",
          "parts": [
            {
              "text": "Sorry, I don't have timezone information for New York."
            }
          ]
        }
      },
      "expected_tool_calls": [
        {
          "name": "get_current_time",
          "args": {
            "query": "New York"
          }
        }
      ]
    }
  ]
}
EOF
```

### 2. Update the Evaluation Config (`tests/eval/eval_config.yaml`)
Configure both the LLM-as-a-judge response quality metric (`custom_response_quality`) and a deterministic tool-trajectory check (`tool_trajectory_match`):

```bash
cat << 'EOF' > tests/eval/eval_config.yaml
# Evaluation configuration for local and cloud grading.
# Run `agents-cli eval metric list` to see available built-in metrics.

metrics_to_run:
  - custom_response_quality
  - tool_trajectory_match

custom_metrics:
  - name: custom_response_quality
    custom_function_file: response_quality.py

  - name: tool_trajectory_match
    custom_function: |
      def evaluate(instance):
          expected = instance.get("expected_tool_calls") or []
          actual = [
              part["function_call"]
              for turn in (instance.get("agent_data") or {}).get("turns", [])
              for event in turn.get("events", [])
              for part in (event.get("content") or {}).get("parts", [])
              if "function_call" in part
          ]
          actual_norm = [{"name": c.get("name"), "args": c.get("args", {})} for c in actual]
          score = 1.0 if actual_norm == expected else 0.0
          return {"score": score, "explanation": f"Expected {expected}, got {actual_norm}"}
EOF
```

### 3. Run the Evaluation Suite

#### 🤖 With a Coding Agent
> *"Run the evaluation suite for my agent."*

#### 👤 Manual Mode
```bash
agents-cli eval run
```

**Expected Output:**
* `custom_response_quality`: `1.00` (2/2 passed)
* `tool_trajectory_match`: `1.00` (2/2 passed)
* Interactive HTML report generated under `artifacts/grade_results/results_<timestamp>.html`.

---

## Step 9: Add Agent Runtime Deployment & Run Pre-Deployment Tests

Enhance your prototype project with the **Agent Runtime** deployment target:

### 🤖 With a Coding Agent
> *"Add Agent Runtime deployment to my project and run the unit and integration tests."*

### 👤 Manual Mode
1. Add the `agent_runtime` deployment target:
   ```bash
   agents-cli scaffold enhance . --deployment-target agent_runtime --yes
   ```
2. Run the unit and integration test suite (passing `--env-file .env` so Vertex AI environment variables are loaded):
   ```bash
   uv run --env-file .env pytest tests/unit tests/integration
   ```

---

## Step 10: Deploy to Agent Runtime

### 🤖 With a Coding Agent
> *"Deploy my agent to Agent Runtime in project `YOUR_PROJECT_ID`, region `us-central1`."*

### 👤 Manual Mode
1. Generate a clean `uv.lock` file against public PyPI (using `--no-config` ensures any corporate/private PyPI mirror configured on your workstation is not baked into `uv.lock` when Cloud Build builds the container):
   ```bash
   rm -f uv.lock && uv lock --no-config
   ```
2. Deploy the agent to Agent Runtime (takes ~5–8 minutes):
   ```bash
   agents-cli deploy --project "$GOOGLE_CLOUD_PROJECT" --region "$GOOGLE_CLOUD_LOCATION"
   ```

When deployment completes, the CLI writes the Reasoning Engine resource ID to `deployment_metadata.json` and prints your **Console Playground** URL.

---

## Step 11: Test and Monitor Your Deployed Agent

### Option 1: Google Cloud Console Playground
Click the **Console Playground** link printed at the end of Step 10:
```text
https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/us-central1/agent-engines/<RUNTIME_ID>/playground?project=<YOUR_PROJECT_ID>
```

### Option 2: Query the Deployed Agent via `agents-cli run`
```bash
RUNTIME_ID=$(jq -r .remote_agent_runtime_id deployment_metadata.json)

agents-cli run \
  --url "https://${GOOGLE_CLOUD_LOCATION}-aiplatform.googleapis.com/v1/${RUNTIME_ID}" \
  --mode adk \
  "What's the weather in San Francisco?"
```

---

## Step 12: Optional — Publish to Gemini Enterprise

Register your deployed Agent Runtime agent with an existing **Gemini Enterprise** app in your project:

### 🤖 With a Coding Agent
> *"Publish my agent to my Gemini Enterprise app `<YOUR_APP_ID>`."*

### 👤 Manual Mode
1. List the Gemini Enterprise apps in your project to find the full resource name (`projects/<PROJECT_NUMBER>/locations/global/collections/default_collection/engines/<YOUR_APP_ID>`):
   ```bash
   agents-cli publish gemini --list --project "$GOOGLE_CLOUD_PROJECT"
   ```
2. Register your agent with Gemini Enterprise in native `adk` mode:
   ```bash
   agents-cli publish gemini \
     --gemini-app-id "projects/PROJECT_NUMBER/locations/global/collections/default_collection/engines/YOUR_APP_ID" \
     --display-name "Customer Support Agent" \
     --description "Customer support agent that provides weather information and local time for cities." \
     --tool-description "Provides current weather and time information for cities." \
     --registration-type adk
   ```

---

## Step 13: Clean Up

To avoid incurring ongoing charges, delete the deployed Agent Runtime instance when you are finished:

```bash
RUNTIME_ID=$(jq -r .remote_agent_runtime_id deployment_metadata.json)

curl -X DELETE \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://${GOOGLE_CLOUD_LOCATION}-aiplatform.googleapis.com/v1beta1/${RUNTIME_ID}?force=true"
```
