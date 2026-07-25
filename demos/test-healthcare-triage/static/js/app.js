document.getElementById('send-btn').addEventListener('click', async () => {
    const input = document.getElementById('query-input');
    const output = document.getElementById('chat-output');
    if (!input.value) return;
    
    output.innerHTML += `<div><strong>User:</strong> ${input.value}</div>`;
    const query = input.value;
    input.value = '';
    
    try {
        const res = await fetch('/api/query', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query})
        });
        const data = await res.json();
        output.innerHTML += `<div style="color: #38bdf8; margin-top: 0.5rem;"><strong>Agent:</strong> ${data.agent_response}</div>`;
    } catch (e) {
        output.innerHTML += `<div style="color: #ef4444;">Error processing request.</div>`;
    }
});
