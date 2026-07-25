import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.agent import root_agent
from app.simulation import get_simulated_response

app = FastAPI(title="Test Healthcare Triage Assistant Service")

@app.post("/api/query")
async def handle_query(payload: dict):
    user_input = payload.get("query", "Hello")
    return get_simulated_response(user_input)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
