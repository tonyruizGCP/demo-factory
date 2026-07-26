document.addEventListener('DOMContentLoaded', () => {
    const queryInput = document.getElementById('query-input');
    const sendBtn = document.getElementById('send-btn');
    const chatOutput = document.getElementById('chat-output');
    const sampleBtns = document.querySelectorAll('.sample-btn');

    sampleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            queryInput.value = btn.dataset.query;
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

        // Append User Message
        appendMessage(text, 'user');
        queryInput.value = '';

        try {
            const res = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: text })
            });

            const data = await res.json();
            
            let replyText = `🤖 <strong>Agent Response:</strong>\n${data.agent_response}\n\n`;
            replyText += `🔍 <strong>OAuth Resolution:</strong> ${data.oauth_stage}\n`;
            replyText += `📊 <strong>Quality Scores:</strong> Quality: ${(data.eval_scores.FINAL_RESPONSE_QUALITY*100).toFixed(0)}%, Trajectory: ${(data.eval_scores.TRAJECTORY_COMPLIANCE*100).toFixed(0)}%, Safety: ${(data.eval_scores.SAFETY_GUARDRAILS*100).toFixed(0)}%`;

            appendMessage(replyText, 'agent');
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
