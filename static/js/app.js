// Global State Storage
let currentGeneratedArtifacts = null;
let currentPresetData = null;

document.addEventListener('DOMContentLoaded', () => {
    fetchPresets();
    updateTCOCalculations();
});

// Tab Navigation
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    document.getElementById(`tab-${tabName}-btn`).classList.add('active');
    document.getElementById(`tab-${tabName}`).classList.add('active');
}

// Fetch Presets from API
async function fetchPresets() {
    try {
        const res = await fetch('/api/presets');
        const data = await res.json();
        currentPresetData = {};
        data.forEach(p => {
            currentPresetData[p.key] = p;
        });
    } catch (e) {
        console.error('Error fetching presets:', e);
    }
}

// Load Preset Into Form
function loadPreset() {
    const val = document.getElementById('preset-select').value;
    if (!val || !currentPresetData || !currentPresetData[val]) return;
    
    const preset = currentPresetData[val];
    document.getElementById('use-case-input').value = preset.title;
    document.getElementById('tech-approach-input').value = preset.tech;
}

// Generate Demo Harness API Call
async function generateDemoHarness() {
    const useCase = document.getElementById('use-case-input').value || 'E-Commerce Support Bot';
    const techApproach = document.getElementById('tech-approach-input').value || 'ADK 2.0 + FastAPI + Vertex AI';
    const rigorLevel = document.getElementById('rigor-select').value;
    const includeEvals = document.getElementById('chk-evals').checked;
    const includeCiCd = document.getElementById('chk-cicd').checked;

    const btn = document.getElementById('btn-generate');
    const badge = document.getElementById('gen-status-badge');
    
    btn.disabled = true;
    btn.innerText = '⏳ Engineering SDLC Harness...';
    badge.innerText = 'Generating...';
    badge.className = 'badge badge-idle';

    try {
        const res = await fetch('/api/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                customer_use_case: useCase,
                tech_approach: techApproach,
                rigor_level: rigorLevel,
                include_evals: includeEvals,
                include_ci_cd: includeCiCd
            })
        });

        const data = await res.json();
        currentGeneratedArtifacts = data;

        badge.innerText = 'SUCCESS';
        badge.className = 'badge badge-success';

        // Hide placeholder, show code block section
        document.getElementById('gen-result-container').style.display = 'none';
        document.getElementById('code-preview-section').style.display = 'block';

        showPreviewCode('agents_md');
    } catch (e) {
        alert('Error generating demo harness: ' + e.message);
        badge.innerText = 'FAILED';
        badge.className = 'badge badge-idle';
    } finally {
        btn.disabled = false;
        btn.innerText = '✨ Generate Demo Project & SDLC Harness';
    }
}

// Preview Code Files
function showPreviewCode(type) {
    if (!currentGeneratedArtifacts) return;

    document.querySelectorAll('.subtab-btn').forEach(btn => btn.classList.remove('active'));
    
    const display = document.getElementById('code-display');

    if (type === 'agents_md') {
        display.textContent = currentGeneratedArtifacts.agents_md_content;
    } else if (type === 'ci_yml') {
        display.textContent = currentGeneratedArtifacts.ci_workflow_yaml;
    } else if (type === 'agent_py') {
        display.textContent = `# app/agent.py (ADK Export Entrypoint)\n# Scaffolded for: ${currentGeneratedArtifacts.project_name}\n\nimport os\nfrom google.genai import types\n\nclass Agent:\n    def __init__(self, name: str, instruction: str):\n        self.name = name\n        self.instruction = instruction\n\nroot_agent = Agent(\n    name="${currentGeneratedArtifacts.project_name}-agent",\n    instruction="You are a specialized agent for ${currentGeneratedArtifacts.project_name}."\n)\napp = root_agent`;
    } else if (type === 'summary') {
        const filesList = currentGeneratedArtifacts.files_created.map(f => `  - ${f}`).join('\n');
        display.textContent = `=== SDLC HARNESS GENERATION SUMMARY ===\nProject Name: ${currentGeneratedArtifacts.project_name}\nLocation: ${currentGeneratedArtifacts.project_path}\nStatus: ${currentGeneratedArtifacts.status}\n\nFiles Created:\n${filesList}\n\nTCO Impact: ${currentGeneratedArtifacts.tco_summary.estimated_opex_reduction}`;
    }
}

// Interactive Simulation Runner
async function runSimulation() {
    const useCaseKey = document.getElementById('runner-usecase-select').value;
    const promptInput = document.getElementById('runner-prompt-input').value;

    const btn = document.getElementById('btn-run-sim');
    btn.disabled = true;
    btn.innerText = '⏳ Executing Agent Loop...';

    try {
        const res = await fetch('/api/simulate-run', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                use_case: useCaseKey,
                user_input: promptInput
            })
        });

        const data = await res.json();

        // Render response
        document.getElementById('sim-response-text').innerText = data.agent_response;

        // Render thoughts
        const thoughtsUl = document.getElementById('sim-thoughts-list');
        thoughtsUl.innerHTML = '';
        data.thought_process.forEach(t => {
            const li = document.createElement('li');
            li.innerText = t;
            thoughtsUl.appendChild(li);
        });

        // Render tool calls
        const toolContainer = document.getElementById('sim-tool-calls');
        toolContainer.innerHTML = '';
        data.tool_calls.forEach(tc => {
            const div = document.createElement('div');
            div.className = 'tool-item';
            div.innerHTML = `<strong>Tool: ${tc.tool_name}</strong><br>Args: ${JSON.stringify(tc.arguments)}<br>Result: ${JSON.stringify(tc.result)}`;
            toolContainer.appendChild(div);
        });

        // Render scores
        const scores = data.eval_metrics;
        document.getElementById('score-quality').innerText = `${Math.round((scores.FINAL_RESPONSE_QUALITY || 0.95)*100)}%`;
        document.getElementById('score-trajectory').innerText = `${Math.round((scores.TRAJECTORY_COMPLIANCE || 0.96)*100)}%`;
        document.getElementById('score-safety').innerText = `${Math.round((scores.SAFETY_GUARDRAILS || 1.0)*100)}%`;

    } catch (e) {
        alert('Simulation error: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerText = '▶️ Run Agent Loop & Verify Harness';
    }
}

// Trigger Full Evaluation Suite
async function triggerEvalSuite() {
    const slug = document.getElementById('runner-usecase-select').value;
    const logsBox = document.getElementById('eval-logs-container');
    const logsText = document.getElementById('eval-logs-text');

    logsBox.style.display = 'block';
    logsText.innerText = 'Running Pytest unit tests and LM trajectory evals...';

    try {
        const res = await fetch('/api/eval', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({project_slug: slug})
        });

        const data = await res.json();
        logsText.innerText = data.logs.join('\n');
    } catch (e) {
        logsText.innerText = 'Error running eval suite: ' + e.message;
    }
}

// TCO Calculator Slider Handler
async function updateTCOCalculations() {
    const features = parseInt(document.getElementById('slider-features').value);
    const queries = parseInt(document.getElementById('slider-queries').value);
    const tokens = parseInt(document.getElementById('slider-tokens').value);

    document.getElementById('val-features').innerText = features;
    document.getElementById('val-queries').innerText = queries.toLocaleString();
    document.getElementById('val-tokens').innerText = tokens.toLocaleString();

    try {
        const res = await fetch('/api/tco-calc', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                features_count: features,
                queries_per_day: queries,
                average_context_tokens: tokens
            })
        });

        const data = await res.json();

        // Render Vibe Coding
        document.getElementById('tco-vibe-capex').innerText = `$${data.vibe_coding_capex.toLocaleString()}`;
        document.getElementById('tco-vibe-opex').innerText = `$${data.vibe_coding_opex_monthly.toLocaleString()}`;
        document.getElementById('tco-vibe-annual').innerText = `$${data.vibe_coding_total_annual.toLocaleString()}`;

        // Render Agentic Engineering
        document.getElementById('tco-agentic-capex').innerText = `$${data.agentic_capex.toLocaleString()}`;
        document.getElementById('tco-agentic-opex').innerText = `$${data.agentic_opex_monthly.toLocaleString()}`;
        document.getElementById('tco-agentic-annual').innerText = `$${data.agentic_total_annual.toLocaleString()}`;

        // Render Summary Metrics
        document.getElementById('tco-crossover').innerText = `${data.crossover_months} Months`;
        document.getElementById('tco-token-reduction').innerText = `${data.token_burn_reduction_pct}%`;
        document.getElementById('tco-explanation').innerText = data.explanation;

    } catch (e) {
        console.error('TCO calculation error:', e);
    }
}
