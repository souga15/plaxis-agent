from contextlib import asynccontextmanager
from pathlib import Path
# Make sure env vars are loaded BEFORE importing other modules
from dotenv import load_dotenv
load_dotenv()

import json
import logging
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from plaxis_connection import connection_manager
from agent import agent
from tool_dispatcher import dispatch_tool_calls

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DASHBOARD_PATH = Path(__file__).resolve().parent / "dashboard" / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Attempt connection on startup (non-fatal if Plaxis isn't running yet)
    try:
        connection_manager.connect()
    except Exception as e:
        logger.warning(f"Could not connect to Plaxis on startup: {e}")
        logger.info("You can connect later once Plaxis scripting server is enabled.")
    yield


app = FastAPI(lifespan=lifespan)


def build_status_payload():
    input_connected = connection_manager.g_i is not None
    output_connected = connection_manager.g_o is not None
    return {
        "type": "status",
        "connected": input_connected,
        "input_connected": input_connected,
        "output_connected": output_connected,
    }

@app.get("/")
async def get_dashboard():
    with DASHBOARD_PATH.open("r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/api/status")
async def get_status():
    return {
        "plaxis_connected": connection_manager.is_connected,
        "input_server": connection_manager.g_i is not None,
        "output_server": connection_manager.g_o is not None,
    }

@app.post("/api/reconnect")
async def reconnect():
    success = connection_manager.reconnect()
    return {"success": success, "connected": connection_manager.is_connected}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Send initial status
    await websocket.send_json(build_status_payload())

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "prompt":
                prompt = msg.get("text", "")
                if not prompt.strip():
                    continue

                try:
                    # Step 1: Get LLM response with tool call plan
                    response = await agent.process_request(prompt)
                    tool_calls = response.get("tool_calls", [])
                    llm_message = response.get("message", "Processed your request.")

                    # Step 2: ACTUALLY EXECUTE the tool calls against Plaxis
                    if tool_calls:
                        results = dispatch_tool_calls(tool_calls)
                        compatibility_issue_found = any(r.get("compatibility_issue") for r in results)
                        
                        # Build detailed reply with execution results
                        reply = llm_message + "\n\n\U0001f4cb **Execution Results:**\n"
                        if compatibility_issue_found:
                            reply = (
                                "\u26a0\ufe0f **PLAXIS scripting compatibility warning:** "
                                "the connected PLAXIS build does not appear to expose the commands "
                                "or attributes this agent expects. This usually points to a PLAXIS "
                                "version/API mismatch or an unsupported installation.\n\n"
                                + reply
                            )
                        for r in results:
                            status_icon = "\u2705" if r["success"] else "\u274c"
                            reply += f"\n{status_icon} `{r['tool']}`: {r['result']}"
                    else:
                        reply = llm_message

                    await websocket.send_json({
                        "type": "chat",
                        "message": reply
                    })

                except Exception as e:
                    logger.error(f"Error processing prompt: {traceback.format_exc()}")
                    await websocket.send_json({
                        "type": "chat",
                        "message": f"\u26a0\ufe0f Error: {str(e)}"
                    })

            elif msg.get("type") == "reconnect":
                success = connection_manager.reconnect()
                await websocket.send_json(build_status_payload())

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {traceback.format_exc()}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
