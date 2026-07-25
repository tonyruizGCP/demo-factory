async function sendAlertWebhook() {
    const severity = document.getElementById('severity-select').value;
    const service = document.getElementById('service-input').value;
    const output = document.getElementById('triage-output');
    const badge = document.getElementById('triage-status');

    output.innerText = 'Transmitting webhook alert to ADK 2.0 triage agent...';

    const alertPayload = {
        alert_id: 'ALT-' + Math.floor(1000 + Math.random() * 9000),
        severity: severity,
        service_name: service,
        error_message: severity === 'CRITICAL' ? 'Fatal: Database pool exhausted, 504 gateway timeout' : 'Cache miss ratio exceeded 15%',
        timestamp: new Date().toISOString()
    };

    try {
        const res = await fetch('/webhook', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(alertPayload)
        });
        const data = await res.json();
        
        badge.innerText = `Status: ${data.status} | Node: ${data.node}`;
        if (data.report_markdown) {
            output.innerText = data.report_markdown;
        } else {
            output.innerText = `[AUTO RESOLVED]\n${data.summary}`;
        }
    } catch (e) {
        output.innerText = 'Webhook Error: ' + e.message;
    }
}
