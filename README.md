# PLAXIS AI Automation Agent

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![WebSocket](https://img.shields.io/badge/Realtime-WebSockets-orange.svg)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![LLM Provider](https://img.shields.io/badge/LLM-Anthropic%20Claude%203.5-red.svg)](https://www.anthropic.com/)
[![Executable](https://img.shields.io/badge/Desktop-Single--File%20EXE-purple.svg)](#compilation--desktop-distribution)

An enterprise-ready AI automation agent designed to automate geotechnical modeling and result extraction in PLAXIS 2D/3D using natural language commands. Features a premium side-by-side split-screen dashboard, a real-time auto-synchronized CAD simulation engine, and an autonomous, self-correcting multi-agent optimization swarm powered by **Anthropic Claude 3.5**.

---

## System Architecture

The system coordinates specialized sub-agents, live remote scripting RPC endpoints, and a responsive WebSocket dashboard:

```
┌────────────────────────────────────────────────────────┐
│             Premium Split-Screen Web GUI               │
│  ┌──────────────────────────┬───────────────────────┐  │
│  │   AI Chat & Markdown     │  Live CAD Simulation  │  │
│  │     Logs (Left)          │  Viewport (Right)     │  │
│  └──────────────────────────┴───────────────────────┘  │
└──────────────────────────┬─────────────────────────────┘
                           │ (Bi-directional WebSockets)
                           ▼
┌────────────────────────────────────────────────────────┐
│             FastAPI Production API Server              │
│  - Captures /api/model/screenshot                      │
│  - Feeds realtime model & soil profile updates         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            Geotechnical Multi-Agent Swarm              │
│  Geometry, Calculations, and Verification Loops        │
└──────────────────────────┬─────────────────────────────┘
                           │ (PLAXIS Remote Scripting RPC)
                           ▼
┌────────────────────────────────────────────────────────┐
│            Active PLAXIS Geotechnical Engine           │
│  Creates grids, boreholes, runs finite element mesh    │
└──────────────────────────┬─────────────────────────────┘
```

---

## Key Features

* **Claude 3.5 Geotechnical Swarm**: Uses advanced prompts optimized for Anthropic Claude 3.5, providing highly reliable command sequencing, complex logic execution, and formal engineering report formatting.
* **Premium Split-Screen Workspace**: Features a sleek side-by-side split viewport. Left pane hosts the conversation with structured markdown rendering (via `marked.js`), and the right pane shows the real-time active finite element model!
* **Auto-Synchronized CAD Simulation Viewport**:
  * **Connected Mode**: Triggers `g_i.writepng()` inside PLAXIS to serve actual pixels of your 3D/2D model.
  * **Simulation / Offline Mode**: Generates a dynamic CAD vector SVG that *updates live* (boreholes, retaining walls, ground anchors, piles, excavations) as you type commands!
* **Geotechnical Model Builder**: Model-aware soil builder GUI tab to configure strata layers, depths, and soil parameters (Mohr-Coulomb, Hardening Soil, Linear Elastic) instantly.
* **Self-Correcting Verification Loops**: Automated optimization cycle. If calculated Safety Factors are below engineering design standards ($FoS < 1.25$), the validation loop dynamically triggers structural reinforcements and recalculates.
* **Cross-Version Resilience Layer**: Built-in CLI command dispatcher (`call_command`) and wrapper try-except blocks to gracefully execute actions across standard, custom, or packaged PLAXIS installations.

---

## Geotechnical Capabilities

| Category | Supported Operations | Key Geotechnical Models & Parameters |
| :--- | :--- | :--- |
| **Geometry** | Boreholes, boundary constraints, soil volumes, plate boundaries | Coordinates ($X, Y, Z$), thicknesses, layers |
| **Materials** | Soil parameters, Plate elastic properties, anchors, interfaces | Mohr-Coulomb, Hardening Soil, Linear Elastic ($\gamma_{sat}$, $\gamma_{unsat}$, $E_{ref}$, $c_{ref}$, $\phi$) |
| **Structures** | Retaining diaphragm walls, node-to-node anchors, embedded beams (piles), loads | Coordinates, anchor spacing, line/surface load intensities ($q_x, q_y, q_z$) |
| **Solvers & Calculations** | Mesh generation, Phase staging, Calculation activation, calculation triggers | Plastic calculations, Safety margin calculations ($Sum-Msf$), Consolidation stages |
| **Data Extraction** | Bending moment diagrams ($M$), Shear ($V$), Axial ($N$), FoS envelopes, deformations | Point query displacement, Excel exports (`openpyxl`) |

---

## Getting Started

For a non-technical setup guide, see [FIRST_TIME_SETUP.md](FIRST_TIME_SETUP.md).

### 1. Configure Credentials
Create a `.env` file in the root directory (or use the Settings tab inside the app):
```env
ANTHROPIC_API_KEY=your_claude_api_key_here
PLAXIS_SIMULATION_MODE=false
```

### 2. Configure PLAXIS Scripting Server
1. Launch **PLAXIS 3D**.
2. Navigate to **Expert** -> **Configure remote scripting server**.
3. Enable the scripting server on port **10000** (Input) and **10001** (Output). Leave the password blank.

### 3. Run from Source
Install dependencies and launch the server:
```powershell
pip install -r requirements.txt
python app.py
```
Open **`http://localhost:8501`** in your browser.

### 4. Simplest Windows Workflow

If you are sharing this with someone who does not code:

1. Build `dist\PlaxisAI.exe`
2. Share the `.exe`
3. Ask them to follow [FIRST_TIME_SETUP.md](FIRST_TIME_SETUP.md)

---

## Compilation & Desktop Distribution

For zero-dependency deployment on client machines, package the application into a standalone Windows desktop executable:

1. Rebuild the distribution binary:
   ```powershell
   .\build.bat
   ```
2. The compilation completes and produces a standalone executable at:
   `dist/PlaxisAI.exe` (~45.4 MB)
3. Share `PlaxisAI.exe` directly. Users can double-click to launch the dashboard and configure credentials directly within the Settings tab.

---

## Automated Test Suite

We keep a resilient critical-path automated test suite verifying connection fallbacks and error handling. Run the suite:
```powershell
python -m pytest tests/ -v
```

---

## License
Geotechnical automation platform is available under the [MIT License](LICENSE).
