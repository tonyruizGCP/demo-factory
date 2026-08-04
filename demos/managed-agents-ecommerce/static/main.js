// UNIFIED COMMERCE AGENT CONTROL ROOM - FRONTEND LOGIC

document.addEventListener('DOMContentLoaded', () => {
  // State
  let currentEnvironmentId = null;
  let isStreaming = false;

  // DOM Elements
  const navItems = document.querySelectorAll('.nav-item');
  const tabPanes = document.querySelectorAll('.tab-pane');

  const chatLog = document.getElementById('chatLog');
  const chatInput = document.getElementById('chatInput');
  const sendChatBtn = document.getElementById('sendChatBtn');
  const envSessionBadge = document.getElementById('envSessionBadge');
  const resetSessionBtn = document.getElementById('resetSessionBtn');

  const triggerCommerce = document.getElementById('triggerCommerce');
  const triggerMarketing = document.getElementById('triggerMarketing');
  const triggerService = document.getElementById('triggerService');

  const catalogGrid = document.getElementById('catalogGrid');
  const customerCardsContainer = document.getElementById('customerCardsContainer');
  const ordersTableBody = document.querySelector('#ordersTable tbody');
  const ticketsTableBody = document.querySelector('#ticketsTable tbody');

  const refreshCatalogBtn = document.getElementById('refreshCatalogBtn');
  const deployAgentBtn = document.getElementById('deployAgentBtn');
  const runDiagBtn = document.getElementById('runDiagBtn');
  const resetSeedBtn = document.getElementById('resetSeedBtn');

  // Diagnostic Elements
  const diagProject = document.getElementById('diagProject');
  const diagLocation = document.getElementById('diagLocation');
  const diagAuth = document.getElementById('diagAuth');
  const diagApi = document.getElementById('diagApi');
  const diagBucket = document.getElementById('diagBucket');
  const sysInstructionsInput = document.getElementById('sysInstructionsInput');

  // Tab Navigation
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetTab = item.getAttribute('data-tab');
      navItems.forEach(i => i.classList.remove('active'));
      tabPanes.forEach(pane => pane.classList.remove('active'));

      item.classList.add('active');
      document.getElementById(targetTab).classList.add('active');

      if (targetTab === 'commerce-tab') loadCatalog();
      if (targetTab === 'marketing-tab') loadCustomers();
      if (targetTab === 'service-tab') loadServiceData();
      if (targetTab === 'control-tab') {
        runDiagnostics();
        loadWorkspaceFiles();
        loadEnvironmentSkills();
      }
    });
  });

  // Load Merchant Database APIs
  async function loadCatalog() {
    try {
      const res = await fetch('/api/merchant/catalog');
      const data = await res.json();
      catalogGrid.innerHTML = data.map(item => `
        <div class="catalog-card">
          <span class="sku-badge">${item.sku}</span>
          <div class="card-title">${item.name}</div>
          <div style="font-size: 13px; color: var(--text-muted);">${item.category} • $${item.price.toFixed(2)}</div>
          <div class="stock-pill ${item.stock_quantity <= 5 ? 'low' : 'ok'}">
            ${item.stock_quantity <= 5 ? `⚠️ Low Stock (${item.stock_quantity} left)` : `In Stock (${item.stock_quantity} units)`}
          </div>
          <div style="font-size: 12px; color: var(--text-sub);">Variants: ${item.colors.join(', ')}</div>
        </div>
      `).join('');
    } catch (e) {
      console.error('Failed to load catalog:', e);
    }
  }

  async function loadCustomers() {
    try {
      const res = await fetch('/api/merchant/customers');
      const data = await res.json();
      customerCardsContainer.innerHTML = data.map(c => `
        <div class="customer-card">
          <div class="cust-header">
            <div>
              <div style="font-weight: 700; font-size: 16px;">${c.name}</div>
              <div style="font-size: 12px; color: var(--text-muted);">${c.email}</div>
            </div>
            <span class="vip-badge ${c.vip_tier}">${c.vip_tier} VIP</span>
          </div>
          <div class="erfm-grid">
            <div class="erfm-item"><div class="lbl">Segment</div><div class="val" style="font-size:11px; color:var(--primary);">${c.erfm_segment}</div></div>
            <div class="erfm-item"><div class="lbl">Recency</div><div class="val">${c.recency_days}d ago</div></div>
            <div class="erfm-item"><div class="lbl">Monetary</div><div class="val">$${c.total_monetary_spend.toFixed(0)}</div></div>
          </div>
          ${c.abandoned_cart ? `
            <div style="background: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.3); padding: 10px; border-radius: 8px; font-size: 12px;">
              <span style="color: var(--accent-marketing); font-weight: 700;">Abandoned Cart:</span> ${c.abandoned_cart.name} ($${c.abandoned_cart.price})
            </div>
          ` : ''}
        </div>
      `).join('');
    } catch (e) {
      console.error('Failed to load customers:', e);
    }
  }

  async function loadServiceData() {
    try {
      const [ordersRes, ticketsRes] = await Promise.all([
        fetch('/api/merchant/orders'),
        fetch('/api/merchant/tickets')
      ]);
      const orders = await ordersRes.json();
      const tickets = await ticketsRes.json();

      ordersTableBody.innerHTML = orders.map(o => `
        <tr>
          <td>#${o.order_id}</td>
          <td>${o.customer_email}</td>
          <td><span style="color: ${o.status.includes('Delayed') ? 'var(--danger)' : 'var(--success)'}; font-weight: 600;">${o.status}</span></td>
          <td>${o.carrier}</td>
          <td style="font-family: var(--font-code);">${o.tracking_number}</td>
          <td>$${o.total_amount.toFixed(2)}</td>
        </tr>
      `).join('');

      ticketsTableBody.innerHTML = tickets.map(t => `
        <tr>
          <td>${t.ticket_id}</td>
          <td>#${t.order_id}</td>
          <td>${t.customer_email}</td>
          <td>${t.subject}</td>
          <td><span class="stock-pill low">${t.priority}</span></td>
          <td>${t.status}</td>
        </tr>
      `).join('');
    } catch (e) {
      console.error('Failed to load service data:', e);
    }
  }

  // Diagnostics & Agent Config
  async function runDiagnostics() {
    try {
      const [diagRes, projRes] = await Promise.all([
        fetch('/api/diagnostics', { method: 'POST' }),
        fetch('/api/project-info')
      ]);
      const diag = await diagRes.json();
      const proj = await projRes.json();

      diagProject.textContent = proj.project_id;
      diagLocation.textContent = proj.location;
      diagBucket.textContent = proj.skill_bucket;
      diagAuth.textContent = diag.auth ? '✅ Valid Application Default Credentials' : '❌ Auth Token Missing';
      diagApi.textContent = diag.api_enabled ? '✅ Enabled (aiplatform.googleapis.com)' : '❌ Disabled';

      sysInstructionsInput.value = `* You are "Omni-AI", an advanced retail assistant designed for OmniCommerce merchants to automate multi-channel engagement and service helpdesks.
* You support three unified pillars: Commerce Cloud (inventory, specs), Marketing Cloud (segment copy, cart recovery), and Service Cloud (helpdesk tickets).
* When starting up, parse the local repository ./merchant_data/ to load product catalogs, active customer order history, and active tickets.
* Always prioritize the customer's eRFM profile (Recency, Frequency, Monetary Value) to recommend upsell products.
* If a customer uses highly frustrated language or requests refunds over $150, draft a structured ticket JSON and trigger the "Escalate to Human Agent" protocol.

Rule: You must always explain your reasoning (e.g., why a promotional offer matches a segment) and narrate your actions.`;
    } catch (e) {
      console.error('Diagnostics error:', e);
    }
  }

  // Workspace Files Inspector
  const workspaceFileSelect = document.getElementById('workspaceFileSelect');
  const workspaceFilePathLabel = document.getElementById('workspaceFilePathLabel');
  const workspaceFileSizeLabel = document.getElementById('workspaceFileSizeLabel');
  const workspaceFileContentViewer = document.getElementById('workspaceFileContentViewer');
  const refreshWorkspaceFilesBtn = document.getElementById('refreshWorkspaceFilesBtn');

  async function loadWorkspaceFiles() {
    try {
      const res = await fetch('/api/environment/workspace');
      const data = await res.json();
      if (data.files && data.files.length > 0) {
        workspaceFileSelect.innerHTML = data.files.map(f => `
          <option value="${f.relative_path}">${f.target_path} (${f.size_bytes} bytes)</option>
        `).join('');
        
        loadSelectedWorkspaceFile(workspaceFileSelect.value);
      }
    } catch (e) {
      console.error('Failed to load workspace files:', e);
    }
  }

  async function loadSelectedWorkspaceFile(relativePath) {
    if (!relativePath) return;
    try {
      const res = await fetch(`/api/environment/workspace/file?path=${encodeURIComponent(relativePath)}`);
      const data = await res.json();
      workspaceFilePathLabel.textContent = data.target_path;
      workspaceFileSizeLabel.textContent = `${data.content.length} characters`;
      workspaceFileContentViewer.value = data.content;
    } catch (e) {
      console.error('Failed to load workspace file content:', e);
    }
  }

  if (workspaceFileSelect) {
    workspaceFileSelect.addEventListener('change', () => {
      loadSelectedWorkspaceFile(workspaceFileSelect.value);
    });
  }

  if (refreshWorkspaceFilesBtn) {
    refreshWorkspaceFilesBtn.addEventListener('click', loadWorkspaceFiles);
  }

  // Environment Skills Inspector
  const skillTargetPathInput = document.getElementById('skillTargetPathInput');
  const skillGcsSourceInput = document.getElementById('skillGcsSourceInput');
  const skillContentViewer = document.getElementById('skillContentViewer');
  const refreshSkillsBtn = document.getElementById('refreshSkillsBtn');

  async function loadEnvironmentSkills() {
    try {
      const res = await fetch('/api/environment/skills');
      const data = await res.json();
      if (data.skills && data.skills.length > 0) {
        const skill = data.skills[0];
        if (skillTargetPathInput) skillTargetPathInput.value = skill.target_path;
        if (skillGcsSourceInput) skillGcsSourceInput.value = skill.gcs_source;
        if (skillContentViewer) skillContentViewer.value = skill.content;
      }
    } catch (e) {
      console.error('Failed to load environment skills:', e);
    }
  }

  if (refreshSkillsBtn) {
    refreshSkillsBtn.addEventListener('click', loadEnvironmentSkills);
  }

  // Reset Session
  resetSessionBtn.addEventListener('click', () => {
    currentEnvironmentId = null;
    envSessionBadge.innerHTML = `<span class="material-symbols-outlined">layers</span> Session: Fresh Container`;
    appendChatMessage('system', 'Session reset. Next prompt will provision a fresh sandbox container.');
  });

  // Seed DB Reset
  resetSeedBtn.addEventListener('click', async () => {
    if (confirm('Reset merchant database to default seed files?')) {
      const res = await fetch('/api/merchant/reset', { method: 'POST' });
      const data = await res.json();
      alert(data.message);
      loadCatalog();
      loadCustomers();
      loadServiceData();
    }
  });

  // Deploy Agent
  deployAgentBtn.addEventListener('click', async () => {
    deployAgentBtn.disabled = true;
    deployAgentBtn.textContent = 'Deploying...';
    try {
      const res = await fetch('/api/agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: 'unified-commerce-agent' })
      });
      const data = await res.json();
      alert(`Agent ${data.id} is ready on Managed Agents Control Plane!`);
    } catch (e) {
      alert('Deployment error: ' + e.message);
    } finally {
      deployAgentBtn.disabled = false;
      deployAgentBtn.innerHTML = `<span class="material-symbols-outlined">rocket_launch</span> Ensure Agent Deployed`;
    }
  });

  // Scenario Triggers
  triggerCommerce.addEventListener('click', () => {
    chatInput.value = "Check inventory for 'UltraBoost Performance Running Shoes' in size 10 and warn me if stock is low!";
    sendMessage();
  });

  triggerMarketing.addEventListener('click', () => {
    chatInput.value = "Draft an abandoned-cart recovery email and a companion SMS for Gold VIP customer Sarah Jenkins who left a leather duffel bag in her cart.";
    sendMessage();
  });

  triggerService.addEventListener('click', () => {
    chatInput.value = "My order #90210 has been delayed for 2 weeks. This is unacceptable, I want a refund!";
    sendMessage();
  });

  // Chat Functionality
  sendChatBtn.addEventListener('click', sendMessage);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || isStreaming) return;

    chatInput.value = '';
    isStreaming = true;
    sendChatBtn.disabled = true;

    // Clear welcome card if present
    const welcome = chatLog.querySelector('.welcome-card');
    if (welcome) welcome.remove();

    appendChatMessage('user', text);

    // Create Agent Message Shell with separated Thoughts Accordion and Clean Response Box
    const agentMsgDiv = document.createElement('div');
    agentMsgDiv.className = 'chat-message agent';
    agentMsgDiv.innerHTML = `
      <span class="msg-sender">Omni-AI</span>
      <div class="agent-message-container">
        <!-- Thoughts Accordion (Default Collapsed) -->
        <div class="thoughts-accordion" style="display: none;">
          <button class="thoughts-toggle-btn">
            <span class="material-symbols-outlined icon-chevron">expand_more</span>
            <span class="material-symbols-outlined" style="font-size: 18px;">psychology</span>
            <span>Agent Reasoning & Tool Traces</span>
            <span class="thoughts-badge">Collapsed</span>
          </button>
          <div class="thoughts-content"></div>
        </div>

        <!-- Clean Output Response Container -->
        <div class="final-response-box">
          <span style="color: var(--text-muted); font-size: 13px;"><em>*[Analyzing data & processing query...]*</em></span>
        </div>
      </div>
    `;
    chatLog.appendChild(agentMsgDiv);
    chatLog.scrollTop = chatLog.scrollHeight;

    const accordionEl = agentMsgDiv.querySelector('.thoughts-accordion');
    const toggleBtn = agentMsgDiv.querySelector('.thoughts-toggle-btn');
    const thoughtsContentEl = agentMsgDiv.querySelector('.thoughts-content');
    const responseBoxEl = agentMsgDiv.querySelector('.final-response-box');

    toggleBtn.addEventListener('click', () => {
      toggleBtn.classList.toggle('expanded');
      const badge = toggleBtn.querySelector('.thoughts-badge');
      if (thoughtsContentEl.classList.contains('open')) {
        thoughtsContentEl.classList.remove('open');
        if (badge) badge.textContent = 'Collapsed';
      } else {
        thoughtsContentEl.classList.add('open');
        if (badge) badge.textContent = 'Expanded';
      }
    });

    let thoughtsText = '';
    let responseText = '';

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent: 'unified-commerce-agent',
          input: text,
          environment: currentEnvironmentId || 'remote'
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (!dataStr) continue;

            try {
              const event = JSON.parse(dataStr);
              if (event.type === 'env_id' && event.env_id) {
                currentEnvironmentId = event.env_id;
                envSessionBadge.innerHTML = `<span class="material-symbols-outlined">layers</span> Environment: ${currentEnvironmentId.substring(0, 18)}...`;
              }
              if (event.type === 'thought' && event.text) {
                accordionEl.style.display = 'block';
                thoughtsText += event.text;
                thoughtsContentEl.innerHTML = marked.parse(thoughtsText);
              } else if (event.type === 'trace_code' && event.code) {
                accordionEl.style.display = 'block';
                const traceDiv = document.createElement('div');
                traceDiv.className = 'trace-code-block';
                traceDiv.textContent = `[Tool Execution]: ${event.code}`;
                thoughtsContentEl.appendChild(traceDiv);
              } else if (event.type === 'content' && event.text) {
                responseText += event.text;
                
                // Smart Splitter: Extract any preliminary analysis/narration sections into thoughts accordion
                const reasoningHeaders = [
                  "1. Unified Commerce Analysis",
                  "1. Analysis",
                  "### 1. Unified Commerce Analysis",
                  "### 1. Analysis",
                  "My Actions:",
                  "My Reasoning:",
                  "Exploration:"
                ];

                let splitIndex = -1;
                let matchedHeader = "";
                const finalSectionHeaders = ["2. Marketing Cloud", "3. Companion SMS", "### 2.", "### 3."];

                for (const fHeader of finalSectionHeaders) {
                  const idx = responseText.indexOf(fHeader);
                  if (idx !== -1 && (splitIndex === -1 || idx < splitIndex)) {
                    splitIndex = idx;
                    matchedHeader = fHeader;
                  }
                }

                if (splitIndex !== -1 && splitIndex > 0) {
                  accordionEl.style.display = 'block';
                  const thoughtPart = responseText.substring(0, splitIndex);
                  const contentPart = responseText.substring(splitIndex);
                  thoughtsContentEl.innerHTML = marked.parse(thoughtsText + "\n\n" + thoughtPart);
                  responseBoxEl.innerHTML = marked.parse(contentPart);
                } else {
                  responseBoxEl.innerHTML = marked.parse(responseText);
                }
                chatLog.scrollTop = chatLog.scrollHeight;
              }
            } catch (err) {
              // Ignore line parse errors
            }
          }
        }
      }
    } catch (e) {
      responseBoxEl.innerHTML = `<span style="color: var(--danger);">Connection error: ${e.message}</span>`;
    } finally {
      if (!responseText.trim() && thoughtsText.trim()) {
        responseBoxEl.innerHTML = marked.parse(thoughtsText);
      }
      isStreaming = false;
      sendChatBtn.disabled = false;
    }
  }

  function appendChatMessage(sender, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-message ${sender}`;
    msgDiv.innerHTML = `
      <span class="msg-sender">${sender === 'user' ? 'You' : 'System'}</span>
      <div class="msg-bubble">${marked.parse(text)}</div>
    `;
    chatLog.appendChild(msgDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  // Initial Load
  loadCatalog();
});
