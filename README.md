# PLAXIS 3D AI Automation Agent

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![WebSocket](https://img.shields.io/badge/Realtime-WebSockets-orange.svg)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![API Layer](https://img.shields.io/badge/API-PLAXIS%20Remote%20Scripting-lightgrey.svg)](https://www.bentley.com/)

 An advanced, interactive AI assistant designed to automate geotechnical modeling and result extraction in PLAXIS 3D using natural language commands. Seamlessly translates human requests into precise geotechnical operations using an autonomous multi-agent swarm, providing a highly resilient and self-correcting engineering workflow.

---

## System Architecture

The agent functions via a modern event-driven loop that coordinates three specialized sub-agents, connection monitoring, and resilient command dispatch:

```
┌─────────────────────────────────┐
│     Web Dashboard (HTML5)       │ ◄─── Real-time status / Chat logs
└────────────────┬────────────────┘
                 │ (WebSockets)
                 ▼
┌─────────────────────────────────┐
│     FastAPI WebSocket Server     │ ◄─── Manages connections, reads .env
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   Multi-Agent Swarm (A2A)       │ ◄─── Geometry, Solver & Validation Agents
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│     Cross-Version API Layer     │ ◄─── Safe wrappers & CLI fallback execution
└────────────────┬────────────────┘
                 │ (PLAXIS Remote Scripting RPC)
                 ▼
┌─────────────────────────────────┐
│       PLAXIS 3D Engine          │ ◄─── Builds models, meshes, runs FEA
└─────────────────────────────────┘
```

---

## Key Features

* **Multi-Agent Geotechnical Swarm**: Distributes responsibilities among three specialized sub-agents (`GeometryAgent`, `CalculationAgent`, and `ValidationAgent`) coordinating a linear engineering pipeline.
* **Self-Correcting Design Loop**: Implements automated feedback loops. If the `ValidationAgent` computes a safety factor below standard limits ($FoS < 1.25$), it automatically constructs correction instructions and triggers the `GeometryAgent` to strengthen structural elements and recalculate.
* **Spatial Query Engine**: Incorporates a coordinate-based bounding-box lookup engine (`find_object_by_coordinates`), completely bypassing fragile proxy string name guesses (e.g. `Volume_1_1`) when geometries split during meshing.
* **Strict Pydantic Validation**: Uses robust `pydantic` schemas to parse and type-check LLM tool outputs, keeping arguments safe, precise, and structurally verified before execution.
* **Soil Profile Builder**: A model-aware interactive GUI tab to define layers, depths, and soil parameters (Mohr-Coulomb, Hardening Soil, Linear Elastic) with real-time UI updates.
* **Cross-Version Compatibility Layer**: Implements automatic, resilient CLI commands (`call_command`) and dynamic mode transitions (`gotosoil`, `gotostructures`, `gotomesh`, `gotostages`) to ensure compatibility across official, custom, and repackaged PLAXIS builds.
* **Real-time Status Feed**: Dual-server WebSocket lights that display the connection state of the Input and Output scripting servers independently.
* **XSS & Unicode Safe**: Pure ASCII WebSocket protocol with escaped Unicode representations and sanitization nodes to prevent mojibake and XSS vulnerability risks.

---

## Geotechnical Capabilities

| Category | Supported Operations | Key Geotechnical Models & Parameters |
| :--- | :--- | :--- |
| **Geometry** | Boreholes, Surface boundaries, Volume extrusion, Multi-layer soil profiles | XYZ coordinates, layer boundaries, extrusion vectors |
| **Materials** | Soil Material creation, Plate Material creation, Anchor Material, Assignment logic | Mohr-Coulomb, Hardening Soil, Soft Soil, Linear Elastic, Hoek-Brown, NGI-ADP ($\gamma_{sat}$, $\gamma_{unsat}$, $E_{ref}$, $c_{ref}$, $\phi$, $\psi$) |
| **Structures** | Plates, Ground Anchors, Piles, Interfaces, Surface/Line Loads | Multi-coordinate points, load values ($q_x, q_y, q_z$) |
| **Mesh** | Mesh generation, Local refinement regions, quality logging | Coarseness settings (Very Coarse to Very Fine) |
| **Calculation** | Phase creation, Stage parameters, Active/Inactive states, calculation trigger | Phase Types (Plastic, Safety, Consolidation, Dynamic) |
| **Results** | Displacement vectors ($U_x, U_y, U_z$), Effective Stress tensors, Plate bending moments ($M$), Axial force ($N$), Shear force ($V$), FoS ($Sum-Msf$) | Point-specific query (`getsingleresult`), Model envelope analysis (`getresults`), Excel exports (`openpyxl`) |

---

## Installation & Quick Start

### 1. Download & Extract
1. Click the green **Code** button at the top of this repository and select **Download ZIP**.
2. Unzip the folder to your local working directory.

### 2. Configure Dependencies (Automatic)
Double-click the **`setup.bat`** file located in the root folder.
* **No Python installed?** The script automatically uses Windows `winget` to securely install Python 3.11.
* **Python already configured?** The script installs required Python packages (`fastapi`, `google-genai`, `python-dotenv`, etc.) and walks you through an interactive wizard to configure your Gemini and Groq API keys.

### 3. Open PLAXIS Remote Scripting
1. Launch **PLAXIS 3D**.
2. Navigate to **Expert** -> **Configure remote scripting server**.
3. Enable the scripting server on port **10000** (and port **10001** for Output queries if needed). Leave the password blank.

### 4. Run the Agent
1. Double-click **`run.bat`**. Keep the command window running in the background.
2. Open your web browser and navigate to:
   **`http://localhost:8501`**
3. Switch between **AI Chat** and **Soil Profile Builder** to control your model.

---

## Troubleshooting & Advanced Configuration

> [!NOTE]  
> If the automatic setup fails to configure Python, download Python 3.11 manually from [python.org](https://www.python.org/downloads/). **Ensure you check the box that says "Add Python to PATH" during installation.**

> [!IMPORTANT]  
> If you are using a custom or unofficial PLAXIS build and receive an API exception, the agent will automatically attempt a CLI fallback command. Check the backend server log; it will log a `WARNING: Wrapper gotomode() unavailable, falling back to native command` indicating that the compatibility layer successfully bypassed the API restriction.

---

## License
This project is open-source and available under the [MIT License](LICENSE).
