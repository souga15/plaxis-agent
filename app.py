import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from plaxis_connection import connection_manager
from agent import agent
import json

app = FastAPI()

# Make sure env vars are loaded
from dotenv import load_dotenv
load_dotenv()

@app.on_event("startup")
async def startup_event():
    # Attempt connection on startup
    connection_manager.connect()

@app.get("/")
async def get_dashboard():
    with open("dashboard/index.html", "r") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Send initial status
    await websocket.send_json({
        "type": "status",
        "connected": connection_manager.is_connected
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("type") == "prompt":
                prompt = msg.get("text")
                # process prompt via agent
                response = await agent.process_request(prompt)
                
                # Mock execution: in reality, we would loop through response["tool_calls"]
                # and dynamically call functions from `tools` module here.
                tools_used = len(response.get("tool_calls", []))
                
                reply = response.get("message", "Processed your request.")
                if tools_used > 0:
                    reply += f"\n[Executed {tools_used} Plaxis actions]"
                
                await websocket.send_json({
                    "type": "chat",
                    "message": reply
                })
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
