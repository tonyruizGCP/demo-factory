const currentSessionId = "demo-session-" + Math.random().toString(36).substring(2, 7);

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initPromptChips();
  initChatForm();
  initSessionControls();
  fetchMemories();
  fetchSessionState();
});

// Tab Switcher
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      document.getElementById(targetId).classList.add("active");
    });
  });
}

// Prompt Suggestions
function initPromptChips() {
  document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      document.getElementById("user-input").value = prompt;
      document.getElementById("btn-submit").click();
    });
  });
}

// Chat Form & SSE Stream Handling
function initChatForm() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("user-input");
  const streamContainer = document.getElementById("chat-stream");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const prompt = input.value.trim();
    if (!prompt) return;

    // Append User Message
    appendMessage("user-msg", `<strong>User:</strong> ${prompt}`);
    input.value = "";
    input.disabled = true;
    document.getElementById("btn-submit").disabled = true;

    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: currentSessionId, prompt: prompt })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop(); // Keep partial line in buffer

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.replace("data: ", "").trim();
            if (!dataStr) continue;
            try {
              const eventData = JSON.parse(dataStr);
              handleStreamEvent(eventData);
            } catch (err) {
              console.error("Parse error:", err, dataStr);
            }
          }
        }
      }
    } catch (err) {
      appendMessage("system-msg", `⚠️ Streaming Error: ${err.message}`);
    } finally {
      input.disabled = false;
      document.getElementById("btn-submit").disabled = false;
      input.focus();
      fetchSessionState();
      fetchMemories();
    }
  });
}

function handleStreamEvent(event) {
  const stream = document.getElementById("chat-stream");

  if (event.type === "prewalk_complete") {
    const box = document.createElement("div");
    box.className = "event-box prewalk-box";
    box.innerHTML = `<strong>🔍 PREWALK GROUNDING:</strong> ${event.message}<br>
      <small>Branch: <code>${event.grounding.branch}</code> • Guidelines: ${event.grounding.relevant_guidelines.length}</small>`;
    stream.appendChild(box);
  } else if (event.type === "thought" || event.type === "subagent_thought") {
    const box = document.createElement("div");
    box.className = "event-box thought-box";
    const agentName = event.agent ? `[${event.agent}] ` : "";
    box.innerHTML = `💭 <em>${agentName}${event.content}</em>`;
    stream.appendChild(box);
  } else if (event.type === "tool_call") {
    const box = document.createElement("div");
    box.className = "event-box tool-call-box";
    box.innerHTML = `⚙️ <strong>Tool Call:</strong> <code>${event.name}(${JSON.stringify(event.args)})</code>`;
    stream.appendChild(box);

    if (event.name === "create_worktree_sandbox") {
      document.getElementById("active-wt-name").textContent = event.args.branch_name;
      document.getElementById("diff-content").textContent = 
        `diff --git a/app/services/session_manager.py b/app/services/session_manager.py\n` +
        `--- a/app/services/session_manager.py\n` +
        `+++ b/app/services/session_manager.py\n` +
        `@@ -45,6 +45,14 @@ def add_turn(...)\n` +
        `+    # Async Non-blocking lock integration\n` +
        `+    async with self._lock:\n` +
        `+        return await self._async_write_turn(role, content)\n`;
    }
  } else if (event.type === "tool_output") {
    const box = document.createElement("div");
    box.className = "event-box tool-output-box";
    box.innerHTML = `✔ <strong>Output (${event.name}):</strong> <pre style="margin-top:4px;">${JSON.stringify(event.output, null, 2)}</pre>`;
    stream.appendChild(box);
  } else if (event.type === "memory_consolidated") {
    const box = document.createElement("div");
    box.className = "event-box prewalk-box";
    box.innerHTML = `🧠 <strong>Memory Consolidated:</strong> ${event.memory.content}`;
    stream.appendChild(box);
  } else if (event.type === "final_response") {
    appendMessage("agent-msg", event.content);
  }

  stream.scrollTop = stream.scrollHeight;
}

function appendMessage(className, htmlContent) {
  const stream = document.getElementById("chat-stream");
  const div = document.createElement("div");
  div.className = `message ${className}`;
  div.innerHTML = htmlContent;
  stream.appendChild(div);
  stream.scrollTop = stream.scrollHeight;
}

// Memory Bank Fetcher
async function fetchMemories() {
  try {
    const res = await fetch("/api/memory");
    const data = await res.json();
    const modeBadge = document.getElementById("memory-mode-indicator");
    if (modeBadge && data.mode) {
      modeBadge.textContent = `Mode: ${data.mode.toUpperCase()}`;
      modeBadge.className = data.mode === "managed" ? "badge-mode badge-managed" : "badge-mode badge-local";
    }
    const list = document.getElementById("memory-list");
    list.innerHTML = "";

    data.memories.forEach(m => {
      const card = document.createElement("div");
      card.className = "card";
      const sourceText = (m.metadata && m.metadata.source) ? m.metadata.source : (data.mode === 'managed' ? 'Vertex AI Memory Bank' : 'Local Guideline');
      card.innerHTML = `
        <span class="card-tag">${m.category}</span>
        <p>${m.content}</p>
        <small style="color:var(--text-muted);font-size:0.7rem;">Source: ${sourceText}</small>
      `;
      list.appendChild(card);
    });
  } catch (err) {
    console.error("Error fetching memories:", err);
  }
}

// Session State & Rewind Tree Fetcher
async function fetchSessionState() {
  try {
    const res = await fetch(`/api/session/${currentSessionId}`);
    const data = await res.json();
    const sessionModeBadge = document.getElementById("session-mode-indicator");
    if (sessionModeBadge && data.mode) {
      sessionModeBadge.textContent = `Mode: ${data.mode.toUpperCase()}`;
      sessionModeBadge.className = data.mode === "managed" ? "badge-mode badge-managed" : "badge-mode badge-local";
    }
    const backendBadge = document.getElementById("backend-mode-badge");
    if (backendBadge && data.mode) {
      backendBadge.textContent = `Sessions: ${data.mode.toUpperCase()}`;
      backendBadge.className = data.mode === "managed" ? "badge-mode badge-managed" : "badge-mode badge-local";
    }
    const tree = document.getElementById("turn-history");
    tree.innerHTML = "";

    data.turns.forEach((t, idx) => {
      const node = document.createElement("div");
      node.className = "turn-node";
      node.innerHTML = `
        <div class="turn-info">
          <strong>#${idx + 1} [${t.role.toUpperCase()}]</strong>: ${t.content.substring(0, 40)}...
        </div>
        <button class="btn-rewind" onclick="rewindToTurn('${t.turn_id}')">⏪ Rewind</button>
      `;
      tree.appendChild(node);
    });
  } catch (err) {
    console.error("Error fetching session state:", err);
  }
}

async function rewindToTurn(turnId) {
  if (!confirm(`Are you sure you want to rewind session state to Turn ${turnId}?`)) return;
  try {
    const res = await fetch(`/api/session/${currentSessionId}/rewind`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ turn_id: turnId })
    });
    if (res.ok) {
      appendMessage("system-msg", `⏪ <strong>Session Rewound</strong> to turn <code>${turnId}</code>. State restored.`);
      fetchSessionState();
    }
  } catch (err) {
    alert("Rewind failed: " + err.message);
  }
}

function initSessionControls() {
  document.getElementById("btn-reset-session").addEventListener("click", () => {
    window.location.reload();
  });
}
