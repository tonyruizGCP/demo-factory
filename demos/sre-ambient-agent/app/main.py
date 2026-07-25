import os
import base64
import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.agent import root_agent

app = FastAPI(title="Ambient SRE Log Triage Webhook")

@app.get("/health")
def health():
    return {"status": "HEALTHY", "agent": root_agent.name}

@app.post("/webhook")
async def webhook_handler(request: Request):
    body = await request.json()
    
    # Handle Pub/Sub Push Envelope if present
    if "message" in body and "data" in body["message"]:
        b64_data = body["message"]["data"]
        decoded_bytes = base64.b64decode(b64_data)
        alert_payload = json.loads(decoded_bytes.decode("utf-8"))
    else:
        alert_payload = body
        
    result = root_agent.triage_alert(alert_payload)
    return result

# Serve static files
APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(os.path.dirname(APP_DIR), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

@app.get("/")
def index():
    if os.path.exists(STATIC_DIR):
        return RedirectResponse(url="/static/index.html")
    return {"message": "SRE Ambient Agent API"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
