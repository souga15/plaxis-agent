from contextlib import asynccontextmanager
from pathlib import Path
import sys
import os
# Make sure env vars are loaded BEFORE importing other modules
from dotenv import load_dotenv

def _get_base_dir() -> Path:
    """Return the base directory — works both in dev and when frozen by PyInstaller."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

BASE_DIR = _get_base_dir()

def _get_data_dir() -> Path:
    """Return a writable directory for user data (.env, logs, etc.)."""
    if getattr(sys, 'frozen', False):
        # When running as .exe, store data next to the executable
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

DATA_DIR = _get_data_dir()

# Load .env from data directory (writable location)
_env_path = DATA_DIR / ".env"
load_dotenv(dotenv_path=str(_env_path))

import json
import logging
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.requests import Request
from plaxis_connection import connection_manager
from agent import agent
from tool_dispatcher import dispatch_tool_calls

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DASHBOARD_PATH = BASE_DIR / "dashboard" / "index.html"


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
    active_provider = "None"
    if agent.providers:
        active_provider = agent.providers[0].name
    return {
        "type": "status",
        "connected": input_connected,
        "input_connected": input_connected,
        "output_connected": output_connected,
        "active_provider": active_provider,
        "provider_count": len(agent.providers),
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


# ── Settings API ──────────────────────────────────────────
@app.get("/api/settings")
async def get_settings():
    """Return current API key status (masked) and active provider info."""
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    groq_key = os.getenv("GROQ_API_KEY", "")
    claude_key = os.getenv("ANTHROPIC_API_KEY", "")
    ollama_enabled = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"
    
    def mask(key: str) -> str:
        if not key or key.startswith("your_"):
            return ""
        if len(key) <= 8:
            return "••••••••"
        return key[:4] + "••••" + key[-4:]
    
    active_providers = [p.name for p in agent.providers]
    
    return {
        "gemini_key": mask(gemini_key),
        "groq_key": mask(groq_key),
        "claude_key": mask(claude_key),
        "gemini_configured": bool(gemini_key and not gemini_key.startswith("your_")),
        "groq_configured": bool(groq_key and not groq_key.startswith("your_")),
        "claude_configured": bool(claude_key and not claude_key.startswith("your_")),
        "ollama_enabled": ollama_enabled,
        "active_providers": active_providers,
        "simulation_mode": os.getenv("PLAXIS_SIMULATION_MODE", "false").lower() == "true",
    }

@app.post("/api/settings/update")
async def update_settings(request: Request):
    data = await request.json()
    ollama_enabled = data.get("ollama_enabled")
    if ollama_enabled is not None:
        os.environ["OLLAMA_ENABLED"] = "true" if ollama_enabled else "false"
        agent.reload_providers()
        return {"success": True}
    return {"success": False}

# ── Local AI (Ollama) Endpoints ──────────────────────────
import httpx
import tempfile
import subprocess
from fastapi.responses import StreamingResponse

@app.get("/api/ollama/status")
async def get_ollama_status():
    installed = False
    running = False
    models = []
    
    # Check if command exists
    import shutil
    if shutil.which("ollama"):
        installed = True
        
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                running = True
                installed = True
                models = [m.get("name") for m in resp.json().get("models", [])]
    except Exception:
        pass
        
    return {
        "installed": installed,
        "running": running,
        "models": models,
        "gemma_installed": any("gemma:2b" in m or "gemma" in m for m in models)
    }

@app.post("/api/ollama/install")
async def install_ollama():
    import urllib.request
    try:
        installer_path = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
        # Download if not exists
        if not os.path.exists(installer_path):
            logger.info("Downloading OllamaSetup.exe...")
            urllib.request.urlretrieve("https://ollama.com/download/OllamaSetup.exe", installer_path)
            
        # Launch installer silently
        logger.info(f"Launching installer: {installer_path}")
        # Using startfile to trigger UAC appropriately if needed on Windows
        os.startfile(installer_path)
        return {"success": True, "message": "Installer launched. Please complete the setup."}
    except Exception as e:
        logger.error(f"Failed to install Ollama: {e}")
        return {"success": False, "message": str(e)}

@app.post("/api/ollama/pull")
async def pull_ollama_model():
    """Stream model pulling progress to the client."""
    async def event_generator():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", "http://localhost:11434/api/pull", json={"name": "gemma:2b"}) as response:
                    async for line in response.aiter_lines():
                        if line:
                            yield f"data: {line}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/model/screenshot")
async def get_model_screenshot():
    """
    Attempt to fetch a high-res screenshot from the active PLAXIS Input server.
    If simulation mode is active or extraction fails, return a premium SVG preview.
    """
    import os
    from fastapi.responses import Response, FileResponse
    
    # Try capturing from active PLAXIS server if connected and not simulated
    if connection_manager.is_connected and not connection_manager.is_simulation:
        try:
            # Save screenshot inside writable temp location
            screenshot_path = DATA_DIR / "plaxis_screenshot.png"
            if connection_manager.g_i:
                connection_manager.g_i.writepng(str(screenshot_path))
                if screenshot_path.exists() and screenshot_path.stat().st_size > 0:
                    return FileResponse(str(screenshot_path), media_type="image/png")
        except Exception as e:
            logger.warning(f"Could not capture real Plaxis screenshot: {e}")

    # Get simulation state values if in simulation mode
    g = connection_manager.g_i
    has_excavation = getattr(g, "has_excavation", False)
    has_retaining_wall = getattr(g, "has_retaining_wall", False)
    has_anchors = getattr(g, "has_anchors", False)
    has_piles = getattr(g, "has_piles", False)

    # Conditionally generate SVG elements based on active geotechnical structures
    excavation_html = ""
    mesh_html = ""
    if has_excavation:
        excavation_html = '<polygon points="250,80 280,180 520,180 550,80" fill="#11141a" stroke="#2a2d3a" stroke-width="2"/>'
        mesh_html = """
        <path d="M 280,180 L 330,180 L 305,220 Z" fill="none" stroke="#00c9b1" stroke-width="0.5" opacity="0.4"/>
        <path d="M 330,180 L 400,180 L 365,220 Z" fill="none" stroke="#00c9b1" stroke-width="0.5" opacity="0.4"/>
        <path d="M 400,180 L 470,180 L 435,220 Z" fill="none" stroke="#00c9b1" stroke-width="0.5" opacity="0.4"/>
        <path d="M 470,180 L 520,180 L 495,220 Z" fill="none" stroke="#00c9b1" stroke-width="0.5" opacity="0.4"/>
        """

    retaining_wall_html = ""
    if has_retaining_wall:
        retaining_wall_html = """
        <rect x="247" y="70" width="8" height="180" fill="#00c9b1" opacity="0.9" rx="2"/>
        <rect x="545" y="70" width="8" height="180" fill="#00c9b1" opacity="0.9" rx="2"/>
        <text x="180" y="60" fill="#e2e8f0" font-family="'Inter', sans-serif" font-size="10" opacity="0.7">Diaphragm Wall (t=0.5m)</text>
        """

    anchors_html = ""
    if has_anchors:
        anchors_html = """
        <line x1="247" y1="120" x2="160" y2="160" stroke="#6c63ff" stroke-width="3" stroke-dasharray="2,2"/>
        <circle cx="160" cy="160" r="4" fill="#6c63ff"/>
        <line x1="553" y1="120" x2="640" y2="160" stroke="#6c63ff" stroke-width="3" stroke-dasharray="2,2"/>
        <circle cx="640" cy="160" r="4" fill="#6c63ff"/>
        <text x="110" y="185" fill="#6c63ff" font-family="'Inter', sans-serif" font-size="10" font-weight="600">Ground Anchors (F_max=500kN)</text>
        """

    piles_html = ""
    if has_piles:
        piles_html = """
        <rect x="330" y="180" width="6" height="150" fill="#00c9b1" opacity="0.7"/>
        <rect x="470" y="180" width="6" height="150" fill="#00c9b1" opacity="0.7"/>
        """

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="100%" height="100%">
        <!-- Background -->
        <rect width="100%" height="100%" fill="#11141a"/>
        <defs>
            <linearGradient id="clay" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="#4a3e3d"/>
                <stop offset="100%" stop-color="#342b2a"/>
            </linearGradient>
            <linearGradient id="sand" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="#cbb893" stop-opacity="0.8"/>
                <stop offset="100%" stop-color="#a89570" stop-opacity="0.8"/>
            </linearGradient>
            <linearGradient id="silt" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="#5a6873"/>
                <stop offset="100%" stop-color="#3e4850"/>
            </linearGradient>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#222733" stroke-width="1"/>
            </pattern>
        </defs>

        <!-- Grid lines -->
        <rect width="100%" height="100%" fill="url(#grid)" />

        <!-- Geological Layers -->
        <!-- Layer 1: Sand (0 to -8m) -->
        <rect x="50" y="80" width="700" height="90" fill="url(#sand)" rx="4"/>
        <!-- Layer 2: Silt (-8m to -18m) -->
        <rect x="50" y="170" width="700" height="110" fill="url(#silt)" rx="4"/>
        <!-- Layer 3: Clay (-18m to -35m) -->
        <rect x="50" y="280" width="700" height="120" fill="url(#clay)" rx="4"/>

        <!-- Structures & Cuts -->
        {excavation_html}
        {retaining_wall_html}
        {anchors_html}
        {piles_html}
        {mesh_html}
        
        <!-- Geological Labels -->
        <text x="60" y="110" fill="#a89570" font-family="'Inter', sans-serif" font-size="11" font-weight="600">Sand Layer (Unsat)</text>
        <text x="60" y="200" fill="#7a8399" font-family="'Inter', sans-serif" font-size="11" font-weight="600">Silt Layer (Water Level)</text>
        <text x="60" y="310" fill="#8a7c7b" font-family="'Inter', sans-serif" font-size="11" font-weight="600">Deep Clay Layer (Consolidation)</text>

        <!-- Compass & Coordinate System -->
        <g transform="translate(730, 390)">
            <line x1="0" y1="0" x2="30" y2="0" stroke="#00c9b1" stroke-width="2"/>
            <line x1="0" y1="0" x2="0" y2="-30" stroke="#6c63ff" stroke-width="2"/>
            <text x="35" y="4" fill="#00c9b1" font-family="sans-serif" font-size="9" font-weight="bold">X</text>
            <text x="-4" y="-35" fill="#6c63ff" font-family="sans-serif" font-size="9" font-weight="bold">Y</text>
        </g>
        
        <rect x="50" y="415" width="700" height="2" fill="#2a2d3a"/>
        <text x="50" y="435" fill="#7a8399" font-family="'Inter', sans-serif" font-size="10">Active Finite Element Mesh: 1,480 Nodes | 2D/3D Equivalent View</text>
    </svg>"""
    return Response(content=svg_content, media_type="image/svg+xml")

@app.post("/api/settings")
async def save_settings(request: Request):
    """Save API keys to .env file and reload providers."""
    body = await request.json()
    
    env_path = DATA_DIR / ".env"
    
    # Read existing values (don't overwrite keys that weren't sent)
    current = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                current[k.strip()] = v.strip()
    
    # Update only the keys that were provided (non-empty)
    key_map = {
        "gemini_key": "GEMINI_API_KEY",
        "groq_key": "GROQ_API_KEY",
        "claude_key": "ANTHROPIC_API_KEY",
    }
    
    for form_key, env_key in key_map.items():
        if form_key in body and body[form_key].strip():
            current[env_key] = body[form_key].strip()
            os.environ[env_key] = body[form_key].strip()
    
    if "simulation_mode" in body:
        sim_val = "true" if body["simulation_mode"] else "false"
        current["PLAXIS_SIMULATION_MODE"] = sim_val
        os.environ["PLAXIS_SIMULATION_MODE"] = sim_val
    
    # Write .env
    try:
        lines = [f"{k}={v}" for k, v in current.items()]
        env_path.write_text("\n".join(lines) + "\n")
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    
    # Reload providers with new keys
    agent.reload_providers()
    
    return {
        "success": True,
        "active_providers": [p.name for p in agent.providers],
    }


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
                        reply = llm_message + "\n\n**Execution Results:**\n"
                        if compatibility_issue_found:
                            reply = (
                                "**[Compatibility Warning]** "
                                "The connected PLAXIS scripting server does not appear to expose the commands "
                                "or attributes this agent expects. This usually points to a PLAXIS "
                                "version/API mismatch or an unsupported installation.\n\n"
                                + reply
                            )
                        for r in results:
                            status_icon = "[Success]" if r["success"] else "[Failure]"
                            reply += f"\n  - {status_icon} `{r['tool']}`: {r['result']}"
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
                        "message": f"**[Error]** {str(e)}"
                    })

            elif msg.get("type") == "reconnect":
                success = connection_manager.reconnect()
                await websocket.send_json(build_status_payload())

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {traceback.format_exc()}")


def _run_server():
    """Start the FastAPI server."""
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8501)


if __name__ == "__main__":
    import threading
    import webbrowser
    import time

    logger.info("Starting PlaxisAI backend server...")
    
    # Start the server exactly ONCE in a background daemon thread
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to bind to port 8501
    time.sleep(1.5)

    try:
        # Open in default web browser natively
        webbrowser.open("http://127.0.0.1:8501")
        logger.info("Launched PlaxisAI in default web browser.")
    except Exception as e:
        logger.warning(f"Could not open browser automatically: {e}")

    # Keep the main thread alive since uvicorn is running as a daemon thread.
    print("\n====================================================")
    print("   PlaxisAI is running at: http://127.0.0.1:8501")
    print("   Press CTRL+C in this terminal to shut down.")
    print("====================================================\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down PlaxisAI...")
        sys.exit(0)

