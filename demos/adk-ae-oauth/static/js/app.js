document.addEventListener('DOMContentLoaded', () => {
    const queryInput = document.getElementById('query-input');
    const sendBtn = document.getElementById('send-btn');
    const chatOutput = document.getElementById('chat-output');
    const sampleBtns = document.querySelectorAll('.sample-btn');
    const tokenInput = document.getElementById('token-input');
    const saveTokenBtn = document.getElementById('save-token-btn');
    const modeSelect = document.getElementById('mode-select');
    const oauthStatusText = document.getElementById('oauth-status-text');

    checkAuthStatus();

    async function checkAuthStatus() {
        try {
            const res = await fetch('/api/auth/status');
            const data = await res.json();
            if (data.has_token) {
                oauthStatusText.textContent = "OAuth Status: Token Active (Stage 1 Cached)";
            } else {
                oauthStatusText.textContent = "OAuth Status: Awaiting Access Token";
            }
        } catch (e) {
            oauthStatusText.textContent = "OAuth Status: Ready";
        }
    }

    saveTokenBtn.addEventListener('click', async () => {
        const token = tokenInput.value.trim();
        if (!token) return;

        try {
            const res = await fetch('/api/auth/token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ oauth_token: token })
            });

            const data = await res.json();
            if (data.status === 'success') {
                oauthStatusText.textContent = "OAuth Status: Token Saved & Verified";
                appendMessage(`✅ <strong>OAuth Token Saved:</strong> Active credentials stored in session. You can now query any live file in your Google Drive.`, 'agent');
                tokenInput.value = '';
            }
        } catch (err) {
            appendMessage(`⚠️ Error saving OAuth token: ${err.message}`, 'agent');
        }
    });

    sampleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            queryInput.value = btn.dataset.query;
            if (btn.dataset.sim === 'true') {
                modeSelect.value = 'sim';
            }
            sendQuery();
        });
    });

    sendBtn.addEventListener('click', sendQuery);
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendQuery();
    });

    async function sendQuery() {
        const text = queryInput.value.trim();
        if (!text) return;

        appendMessage(text, 'user');
        queryInput.value = '';

        const forceSim = modeSelect.value === 'sim';
        const tokenVal = tokenInput.value.trim() || undefined;

        try {
            const res = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: text,
                    oauth_token: tokenVal,
                    force_simulation: forceSim
                })
            });

            const data = await res.json();
            
            let replyText = `🤖 <strong>Agent Response:</strong>\n${data.agent_response}\n\n`;
            if (data.oauth_stage) {
                replyText += `🔍 <strong>OAuth Resolution:</strong> ${data.oauth_stage}\n`;
            }
            if (data.eval_scores) {
                replyText += `📊 <strong>Quality Scores:</strong> Quality: ${(data.eval_scores.FINAL_RESPONSE_QUALITY*100).toFixed(0)}%, Trajectory: ${(data.eval_scores.TRAJECTORY_COMPLIANCE*100).toFixed(0)}%, Safety: ${(data.eval_scores.SAFETY_GUARDRAILS*100).toFixed(0)}%`;
            }

            appendMessage(replyText, 'agent');
            checkAuthStatus();
        } catch (err) {
            appendMessage(`⚠️ Error communicating with ADK OAuth Agent: ${err.message}`, 'agent');
        }
    }

    function appendMessage(msg, type) {
        const msgDiv = document.createElement('div');
        msgDiv.className = type === 'user' ? 'user-msg' : 'agent-msg';
        msgDiv.innerHTML = msg;
        chatOutput.appendChild(msgDiv);
        chatOutput.scrollTop = chatOutput.scrollHeight;
    }
});
