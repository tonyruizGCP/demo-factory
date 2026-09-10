document.addEventListener("DOMContentLoaded", () => {
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("user-input");
  const chatStream = document.getElementById("chat-stream");
  const storeSelect = document.getElementById("store-select");
  const personaSelect = document.getElementById("persona-select");
  const traceTimeline = document.getElementById("trace-timeline");
  const activeSkillInfo = document.getElementById("active-skill-info");
  const viewSkillModalBtn = document.getElementById("view-skill-modal-btn");
  const skillModal = document.getElementById("skill-modal");
  const closeModalBtn = document.getElementById("close-modal-btn");
  const chipButtons = document.querySelectorAll(".chip-btn");

  let skillsCatalog = [];
  let currentSkillName = "store-performance-review";

  // Load Skills from API
  async function loadSkills() {
    try {
      const res = await fetch("/api/registry/skills");
      const data = await res.json();
      skillsCatalog = data.skills || [];
      document.getElementById("skills-count").textContent = `${skillsCatalog.length} Skills`;
      renderSkillList(skillsCatalog);
    } catch (err) {
      console.error("Failed loading skills:", err);
    }
  }

  function renderSkillList(skills) {
    const listContainer = document.getElementById("skills-list");
    listContainer.innerHTML = "";
    skills.forEach((skill) => {
      const card = document.createElement("div");
      card.className = `skill-card ${skill.name === currentSkillName ? "active" : ""}`;
      card.dataset.skill = skill.name;

      const scriptBadge = skill.scripts.length > 0 ? `<span>⚡ ${skill.scripts[0]}</span>` : "";
      const refBadge = skill.references.length > 0 ? `<span>📄 ${skill.references[0]}</span>` : "";

      card.innerHTML = `
        <div class="skill-card-header">
          <strong>${skill.name}</strong>
          <span class="tag-status">Active</span>
        </div>
        <p class="skill-desc">${skill.description || ""}</p>
        <div class="skill-meta">
          ${scriptBadge}
          ${refBadge}
        </div>
      `;

      card.addEventListener("click", () => {
        document.querySelectorAll(".skill-card").forEach(c => c.classList.remove("active"));
        card.classList.add("active");
        currentSkillName = skill.name;
        updateActiveSkillCard(skill);
      });

      listContainer.appendChild(card);
    });
  }

  function updateActiveSkillCard(skill) {
    activeSkillInfo.innerHTML = `
      <strong>${skill.name}</strong>
      <p>${skill.description}</p>
      <button id="view-skill-modal-btn-dynamic" class="btn-secondary">View SKILL.md Spec</button>
    `;
    document.getElementById("view-skill-modal-btn-dynamic").addEventListener("click", () => {
      openModal(skill.name);
    });
  }

  // Quick Chips
  chipButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      userInput.value = btn.dataset.query;
      chatForm.dispatchEvent(new Event("submit"));
    });
  });

  // Simple Markdown Formatter
  function formatMarkdown(text) {
    let html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Headers
    html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");
    html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
    html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");

    // Bold / Italic
    html = html.replace(/\*\*(.*?)\*\*/gim, "<strong>$1</strong>");
    html = html.replace(/\*(.*?)\*/gim, "<em>$1</em>");
    html = html.replace(/`([^`]+)`/gim, "<code>$1</code>");

    // Tables
    const lines = html.split("\n");
    let inTable = false;
    let tableHtml = "";
    let processedLines = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line.startsWith("|") && line.endsWith("|")) {
        if (!inTable) {
          inTable = true;
          tableHtml = "<table>";
          const headers = line.split("|").slice(1, -1);
          tableHtml += "<thead><tr>";
          headers.forEach(h => tableHtml += `<th>${h.trim()}</th>`);
          tableHtml += "</tr></thead><tbody>";
          // Skip divider line if next
          if (i + 1 < lines.length && lines[i+1].includes("---")) {
            i++;
          }
        } else {
          const cells = line.split("|").slice(1, -1);
          tableHtml += "<tr>";
          cells.forEach(c => tableHtml += `<td>${c.trim()}</td>`);
          tableHtml += "</tr>";
        }
      } else {
        if (inTable) {
          inTable = false;
          tableHtml += "</tbody></table>";
          processedLines.push(tableHtml);
        }
        processedLines.push(line);
      }
    }
    if (inTable) {
      tableHtml += "</tbody></table>";
      processedLines.push(tableHtml);
    }

    html = processedLines.join("\n");
    // Lists
    html = html.replace(/^\- (.*$)/gim, "<li>$1</li>");
    html = html.replace(/<li>.*<\/li>/gim, (m) => `<ul>${m}</ul>`);
    html = html.replace(/\n\n/g, "<p></p>");

    return html;
  }

  // Chat Submission
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query) return;

    const storeId = storeSelect.value;
    const persona = personaSelect.value;

    // Append User Message
    appendMessage(query, "user", persona);
    userInput.value = "";

    // Append Assistant Loading Message
    const loadingId = "loading-" + Date.now();
    appendLoadingMessage(loadingId);

    try {
      const res = await fetch("/api/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: query,
          store_id: storeId,
          persona: persona
        })
      });

      const data = await res.json();
      removeMessage(loadingId);

      // Render Final Agent Answer
      appendMessage(data.response, "assistant", "Retail Data Analyst", true);

      // Render Execution Trace
      renderTrace(data.trace);

      // Auto-highlight active skill
      if (data.skill_used) {
        currentSkillName = data.skill_used;
        document.querySelectorAll(".skill-card").forEach(c => {
          c.classList.toggle("active", c.dataset.skill === currentSkillName);
        });
        const matched = skillsCatalog.find(s => s.name === currentSkillName);
        if (matched) updateActiveSkillCard(matched);
      }
    } catch (err) {
      removeMessage(loadingId);
      appendMessage(`⚠️ Error communicating with Agent Platform: ${err.message}`, "assistant", "System");
    }
  });

  function appendMessage(content, sender, label, isMarkdown = false) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-message ${sender}-message`;

    const avatar = sender === "user" ? (label.includes("Manager") ? "👤" : "👔") : "🤖";
    const bodyContent = isMarkdown ? formatMarkdown(content) : `<p>${content}</p>`;

    msgDiv.innerHTML = `
      <div class="msg-avatar">${avatar}</div>
      <div class="msg-body">
        <div style="font-size:11px;font-weight:600;color:var(--text-secondary);margin-bottom:4px;">${label}</div>
        ${bodyContent}
      </div>
    `;

    chatStream.appendChild(msgDiv);
    chatStream.scrollTop = chatStream.scrollHeight;
  }

  function appendLoadingMessage(id) {
    const msgDiv = document.createElement("div");
    msgDiv.id = id;
    msgDiv.className = "chat-message assistant-message";
    msgDiv.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="msg-body" style="display:flex;align-items:center;gap:10px;">
        <span class="dot-flashing" style="font-size:13px;color:var(--google-blue);">Consulting Skill Registry & Querying Retail Tools...</span>
      </div>
    `;
    chatStream.appendChild(msgDiv);
    chatStream.scrollTop = chatStream.scrollHeight;
  }

  function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  // Render Trace Steps
  function renderTrace(traceSteps) {
    traceTimeline.innerHTML = "";
    if (!traceSteps || traceSteps.length === 0) return;

    traceSteps.forEach((step) => {
      const card = document.createElement("div");
      card.className = "trace-card";

      const toolBadge = step.tool ? `<span class="trace-tool">${step.tool}</span>` : "";
      let outputBox = "";
      if (step.output) {
        const text = typeof step.output === "object" ? JSON.stringify(step.output, null, 2) : step.output;
        outputBox = `<div class="trace-output-box">${text}</div>`;
      }

      card.innerHTML = `
        <div class="trace-card-header">
          <span class="trace-phase">${step.phase.replace(/_/g, " ")}</span>
          ${toolBadge}
        </div>
        <div class="trace-detail"><strong>${step.title}</strong></div>
        ${step.detail ? `<div style="font-size:11px;color:var(--text-secondary);margin-top:2px;">${step.detail}</div>` : ""}
        ${outputBox}
      `;

      traceTimeline.appendChild(card);
    });

    traceTimeline.scrollTop = traceTimeline.scrollHeight;
  }

  // Modal Setup
  function openModal(skillName) {
    const skill = skillsCatalog.find(s => s.name === skillName);
    if (!skill) return;

    document.getElementById("modal-skill-title").textContent = `Skill Specification: ${skill.name}`;
    document.getElementById("skill-instructions-code").textContent = skill.full_instructions || "No instructions";
    document.getElementById("skill-script-code").textContent = `# Bundled Python Script\n# Available under scripts/${skill.scripts[0] || 'none'}\n\n# Executable via ADK run_skill_script tool`;
    document.getElementById("skill-reference-code").textContent = `# Reference Guides\n# Bundled in references/${skill.references[0] || 'none'}\n\n# Readable via ADK load_skill_resource tool`;

    skillModal.style.display = "flex";
  }

  viewSkillModalBtn.addEventListener("click", () => openModal(currentSkillName));
  closeModalBtn.addEventListener("click", () => skillModal.style.display = "none");
  window.addEventListener("click", (e) => {
    if (e.target === skillModal) skillModal.style.display = "none";
  });

  // Modal Tabs
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");
    });
  });

  // Initial Load
  loadSkills();
});
