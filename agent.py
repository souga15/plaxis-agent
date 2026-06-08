import json
import re
import logging
from pydantic import BaseModel, Field, ValidationError, model_validator
from typing import List, Dict, Any
from providers.gemini import GeminiProvider
from providers.groq import GroqProvider
from providers.claude import ClaudeProvider

logger = logging.getLogger(__name__)


def _sanitize_llm_json(raw: str) -> str:
    """
    Clean up common LLM JSON formatting mistakes before parsing:
      1. Strip JS-style single-line comments  (// ...)
      2. Strip JS-style block comments        (/* ... */)
      3. Remove trailing commas before ] or }
      4. Extract only the first complete top-level JSON object
         (handles 'Extra data' when the LLM appended explanation text)
    """
    # 1 & 2: strip JS comments (inside strings is handled conservatively)
    raw = re.sub(r"//[^\n\"]*", "", raw)          # single-line // comments
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)  # block /* */ comments

    # 3: trailing commas before ] or }
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    # 4: extract first complete JSON object via brace-counting
    depth = 0
    in_string = False
    escape_next = False
    start = raw.find("{")
    if start == -1:
        return raw
    for i, ch in enumerate(raw[start:], start=start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start: i + 1]
    return raw[start:]  # fallback: return from first { to end


def _project_session_blocked(results: list[dict]) -> bool:
    """Detect failures that mean PLAXIS does not have a usable open project/session yet."""
    for result in results:
        if result.get("success"):
            continue
        text = str(result.get("result", "")).lower()
        if result.get("tool") in {"new_project", "open_project"}:
            return True
        if "create or open a project manually" in text:
            return True
        if "no project is open yet" in text:
            return True
        if "start page" in text:
            return True
    return False

class ToolCall(BaseModel):
    name: str = Field(..., description="Name of the tool to execute")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool")

    @model_validator(mode='before')
    @classmethod
    def extract_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if 'name' not in data:
                if 'tool_name' in data:
                    data['name'] = data['tool_name']
                elif 'tool_code' in data:
                    data['name'] = data['tool_code'].split('(')[0]
            if 'args' not in data:
                if 'parameters' in data:
                    data['args'] = data['parameters']
        return data

class AgentResponse(BaseModel):
    tool_calls: List[ToolCall] = Field(default_factory=list)
    message: str = Field(..., description="Message explaining what actions were taken by this agent")


class GeometryAgent:
    def __init__(self, providers):
        self.providers = providers
        self.system_prompt = """
You are the Geotechnical Geometry Agent.
Your job is to read the user's design constraints and any feedback, then generate structural, material, or coordinate layout tool calls.
You only focus on geometry, boreholes, soils, and physical objects.
IMPORTANT: If you are starting a brand new design from scratch, you MUST call new_project() before calling any other tool!

=== AVAILABLE GEOMETRY & MATERIAL TOOLS ===
- new_project()
- open_project(path: str)
- create_borehole(x: float, y: float, layers: list)
    layers = [{"top": 0, "bottom": -5}, {"top": -5, "bottom": -15}]
- create_surface(points: list) [3D ONLY]
    points = [x1,y1,z1, x2,y2,z2, ...] or [[x1,y1,z1], [x2,y2,z2], ...]
- create_volume(points: list) [3D ONLY] — ONLY takes 'points', no other arguments.
- extrude(object_name: str, direction: list, length: float) [3D ONLY]
- create_polygon(points: list) [2D ONLY]
    points = [x1,y1, x2,y2, ...]
- create_line(points: list) [2D ONLY]
- find_object_by_coordinates(x: float, y: float, z: float, collection: str)
- create_soil_material(name: str, model: str, params: dict)
    model: "Mohr-Coulomb", "Hardening Soil", "Soft Soil", "Linear Elastic"
    params: {"gammaUnsat": 18, "gammaSat": 20, "Eref": 30000, "nu": 0.3, "cref": 10, "phi": 25}
- create_plate_material(name: str, params: dict)
    params: {"d": 0.5, "E1": 30e6, "nu12": 0.15, "w": 12.0}
- create_anchor_material(name: str, params: dict)
- assign_material(object_name: str, material_name: str)
- create_plate(points: list) (2D uses 4 coordinates: [x1,y1,x2,y2])
- create_anchor(point1: list, point2: list) (2D uses [x,y])
- create_pile(point: list, depth: float) (2D uses [x,y])
- create_interface(object_name: str)
- create_load(load_type: str, points: list, value: list) (load_type: 'surface' [3D], 'line', 'point' or 'pointload' [2D])

=== RESPONSE FORMAT ===
You MUST respond with a valid JSON block containing "tool_calls" and "message".
Example:
{
  "tool_calls": [
    {"name": "create_soil_material", "args": {"name": "Clay_Layer", "model": "Mohr-Coulomb", "params": {"gammaUnsat": 16}}}
  ],
  "message": "Created material"
}
If the design is already created or no geometric changes are needed, return an empty tool_calls list.
Always create materials before assigning them.
"""

    async def execute(self, user_prompt: str, design_feedback: str = ""):
        prompt = f"User Request: {user_prompt}\n"
        if design_feedback:
            prompt += f"\nDesign Validation Feedback to address: {design_feedback}\n"
        
        logger.info("[Swarm] Invoking GeometryAgent...")
        return await _call_llm(self.providers, self.system_prompt, prompt)


class CalculationAgent:
    def __init__(self, providers):
        self.providers = providers
        self.system_prompt = """
You are the Solver and Calculation Agent.
Your job is to generate the mesh, define calculation phases, and run calculations.

CRITICAL RULES:
- You MUST ONLY use the tools listed below. DO NOT call create_soil_material, create_borehole, assign_material, or any geometry tool — those have already been handled.
- If geometry/materials are already set up (shown in the geometry log), do NOT repeat them.
- If no calculation is needed (e.g. user only asked for geometry setup), return empty tool_calls.
- DO NOT invent tool names. Only use the exact names listed below.
- Your JSON output must be strictly valid: no comments, no trailing commas.

=== AVAILABLE TOOLS (ONLY THESE) ===
- generate_mesh(fineness: float)  — 0.0=coarse, 0.5=medium, 1.0=fine
- refine_mesh_around(object_name: str, factor: float)
- get_mesh_quality()
- add_phase(name: str, phase_type: str)
    phase_type: "Plastic", "Consolidation", "Safety", "Dynamic"
- activate(phase_name: str, object_name: str)
- deactivate(phase_name: str, object_name: str)
- set_water_level(phase_name: str, level: float)
- list_phases()
- run_calculation()
- get_calculation_status()
- get_log()

=== RESPONSE FORMAT ===
Respond ONLY with a single valid JSON object — no extra text before or after.
{
  "tool_calls": [
    {"name": "generate_mesh", "args": {"fineness": 0.5}}
  ],
  "message": "Generated mesh"
}
If geometry setup was the only goal and no calculation is needed, return: {"tool_calls": [], "message": "No calculation needed for this geometry-only task."}
"""

    async def execute(self, user_prompt: str, geometry_log: str):
        prompt = f"User Request: {user_prompt}\n\nGeometry Actions Completed:\n{geometry_log}"
        logger.info("[Swarm] Invoking CalculationAgent...")
        return await _call_llm(self.providers, self.system_prompt, prompt)


class ValidationAgent:
    def __init__(self, providers):
        self.providers = providers
        self.system_prompt = """
You are the Extraction and Validation Agent.
Your job is to query phase results and verify if the design is safe.

CRITICAL RULES:
- You MUST ONLY use the tools listed below. DO NOT invent tool names like 'evaluate_design_safety' or any tool not in the list.
- If no calculation phase has been run yet, return empty tool_calls — do not attempt to read results.
- If the workflow log shows the Output server is unavailable, return empty tool_calls.
- Your JSON output must be strictly valid: no comments, no trailing commas, no extra text after the closing brace.

=== AVAILABLE TOOLS (ONLY THESE) ===
- get_displacements(phase_name: str, point: list)
- get_stresses(phase_name: str, point: list)
- get_structural_forces(phase_name: str, structure_name: str)
- get_safety_factor(phase_name: str)
- export_results_to_excel(phase_name: str, output_path: str)

=== RESPONSE FORMAT ===
Respond ONLY with a single valid JSON object — no extra text before or after.
{
  "tool_calls": [
    {"name": "get_safety_factor", "args": {"phase_name": "Phase_1"}}
  ],
  "message": "Checked safety"
}
If no safety/calculation phase exists yet, return: {"tool_calls": [], "message": "No calculation phase run yet — skipping results extraction."}
"""

    async def execute(self, user_prompt: str, workflow_log: str):
        prompt = f"User Request: {user_prompt}\n\nWorkflow Execution Progress:\n{workflow_log}"
        logger.info("[Swarm] Invoking ValidationAgent...")
        return await _call_llm(self.providers, self.system_prompt, prompt)


class PlaxisAgentSwarm:
    def __init__(self):
        self.providers = self._init_providers()
        self.geometry_agent = GeometryAgent(self.providers)
        self.calculation_agent = CalculationAgent(self.providers)
        self.validation_agent = ValidationAgent(self.providers)

    def _init_providers(self):
        """Initialize all available LLM providers in priority order."""
        import os
        from providers.ollama_provider import OllamaProvider
        providers = []
        
        # Local Ollama
        if os.getenv("OLLAMA_ENABLED", "false").lower() == "true":
            ollama = OllamaProvider(model_name="gemma:2b")
            if ollama.is_configured():
                providers.append(ollama)
                logger.info("Ollama local provider initialized (priority 1)")

        # Claude first (best tool-calling quality)
        claude = ClaudeProvider()
        if claude.api_key:
            providers.append(claude)
            logger.info(f"Claude provider initialized (priority {len(providers)+1})")
        
        # Gemini second (free, good quality)
        gemini = GeminiProvider()
        if gemini.client:
            providers.append(gemini)
            logger.info(f"Gemini provider initialized (priority {len(providers)+1})")
        
        # Groq third (free, fast)
        groq = GroqProvider()
        if groq.api_key:
            providers.append(groq)
            logger.info(f"Groq provider initialized (priority {len(providers)+1})")
        
        if not providers:
            logger.warning("No AI providers configured! Add API credentials in Settings.")
        
        return providers

    def reload_providers(self):
        """Re-initialize providers after settings change."""
        self.providers = self._init_providers()
        self.geometry_agent.providers = self.providers
        self.calculation_agent.providers = self.providers
        self.validation_agent.providers = self.providers

    async def process_request(self, user_prompt: str):
        """
        Orchestrates the linear multi-agent swarm pipeline:
        Geometry Agent -> Calculation Agent -> Validation Agent.
        If validation shows Safety Factor < 1.25, triggers a feedback loop.
        """
        from tool_dispatcher import dispatch_tool_calls

        if not self.providers:
            return {
                "tool_calls": [],
                "message": (
                    "### API Configuration Required\n\n"
                    "To begin automating your Plaxis design workflows, please configure at least one active API key in the **Settings** view:\n\n"
                    "* **Claude** (Preferred for advanced tool-calling accuracy)\n"
                    "* **Gemini**\n"
                    "* **Groq**"
                )
            }

        swarm_logs = []
        design_feedback = ""
        max_cycles = 2

        for cycle in range(max_cycles):
            cycle_prefix = f"## Design Optimization Cycle {cycle + 1} of {max_cycles}\n"
            swarm_logs.append(cycle_prefix)

            # ---------------------------------------------
            # STEP 1: Geotechnical Geometry Agent
            # ---------------------------------------------
            geo_response = await self.geometry_agent.execute(user_prompt, design_feedback)
            swarm_logs.append(f"### Geometry Design Phase\n{geo_response['message']}")
            
            geo_calls = geo_response.get("tool_calls", [])
            if geo_calls:
                geo_results = dispatch_tool_calls(geo_calls)
                exec_log = "\n".join([f"  - [Success] `{r['tool']}`: {r['result']}" if r["success"] else f"  - [Failure] `{r['tool']}`: {r['result']}" for r in geo_results])
                swarm_logs.append(f"**Geometry Execution Status:**\n{exec_log}")
                geo_log_str = "\n".join([f"- {r['tool']}: Success={r['success']}, Output={r['result']}" for r in geo_results])
                if _project_session_blocked(geo_results):
                    swarm_logs.append(
                        "### Project Setup Required\n"
                        "PLAXIS rejected project/bootstrap commands, so this session does not currently have a usable open project. "
                        "Please create or open a project manually inside PLAXIS 3D, keep Remote Scripting enabled, and then re-issue your request."
                    )
                    return {
                        "tool_calls": [],
                        "message": "\n\n".join(swarm_logs)
                    }
            else:
                geo_log_str = "No geometry updates required."
                swarm_logs.append("*No geometry actions proposed.*")
            
            # ---------------------------------------------
            # STEP 2: Solver & Calculation Agent
            # ---------------------------------------------
            calc_response = await self.calculation_agent.execute(user_prompt, geo_log_str)
            swarm_logs.append(f"### Soil Calculation Phase\n{calc_response['message']}")
            
            calc_calls = calc_response.get("tool_calls", [])
            if calc_calls:
                calc_results = dispatch_tool_calls(calc_calls)
                exec_log = "\n".join([f"  - [Success] `{r['tool']}`: {r['result']}" if r["success"] else f"  - [Failure] `{r['tool']}`: {r['result']}" for r in calc_results])
                swarm_logs.append(f"**Calculation Execution Status:**\n{exec_log}")
                calc_log_str = "\n".join([f"- {r['tool']}: Success={r['success']}, Output={r['result']}" for r in calc_results])
            else:
                calc_log_str = "No calculation actions required."
                swarm_logs.append("*No calculation actions proposed.*")

            # ---------------------------------------------
            # STEP 3: Extraction & Validation Agent
            # ---------------------------------------------
            combined_progress = f"--- Geometry Phase ---\n{geo_log_str}\n\n--- Calculation Phase ---\n{calc_log_str}"
            val_response = await self.validation_agent.execute(user_prompt, combined_progress)
            swarm_logs.append(f"### Extraction & Validation Phase\n{val_response['message']}")
            
            val_calls = val_response.get("tool_calls", [])
            safety_factor = None
            if val_calls:
                val_results = dispatch_tool_calls(val_calls)
                exec_log = "\n".join([f"  - [Success] `{r['tool']}`: {r['result']}" if r["success"] else f"  - [Failure] `{r['tool']}`: {r['result']}" for r in val_results])
                swarm_logs.append(f"**Data Retrieval Status:**\n{exec_log}")
                
                # Check for get_safety_factor output
                for r in val_results:
                    if r["tool"] == "get_safety_factor" and r["success"]:
                        raw = r.get("raw_result")
                        if isinstance(raw, dict) and "safety_factor" in raw:
                            val = raw["safety_factor"]
                            if isinstance(val, (int, float)):
                                safety_factor = val
            else:
                swarm_logs.append("*No result extraction actions proposed.*")

            # ---------------------------------------------
            # STEP 4: Safety Check & Feedback Loop
            # ---------------------------------------------
            if safety_factor is not None:
                swarm_logs.append(
                    f"### Safety Evaluation\n"
                    f"- **Computed Factor of Safety (Sum-Msf):** {safety_factor:.3f}\n"
                    f"- **Target Factor of Safety Threshold:** 1.25"
                )
                if safety_factor < 1.25:
                    if cycle < max_cycles - 1:
                        design_feedback = (
                            f"Safety evaluation FAILED. The computed Safety Factor (Sum-Msf) is {safety_factor:.3f}, "
                            f"which is below our engineering threshold of 1.25. "
                            f"Geometry Agent, please redesign the structure to increase stability (e.g. increase wall thickness, "
                            f"deepen piles, or modify anchor stiffness)."
                        )
                        swarm_logs.append(f"*Safety factor below target threshold. Instructing Geometry Agent to enhance structural support and perform a recalculation...*")
                        swarm_logs.append("\n" + "---" + "\n")
                        continue
                    else:
                        swarm_logs.append(f"### Design Verification Terminated\nThe design has reached the maximum refinement cycles and remains below the target safety margin.")
                else:
                    swarm_logs.append(f"### Design Verification Success\nThe design satisfies all structural and geotechnical safety criteria (FoS >= 1.25).")
                    break
            else:
                # No safety factor retrieved, complete execution
                break

        return {
            "tool_calls": [],  # Swarm executed tools internally
            "message": "\n\n".join(swarm_logs)
        }


async def _call_llm(providers: list, system_prompt: str, prompt: str) -> dict:
    """Try each provider in priority order until one succeeds."""
    last_error = None
    
    for provider in providers:
        try:
            response = await provider.generate_response(system_prompt, prompt)
            logger.info(f"LLM response from {provider.name}")
            break
        except Exception as e:
            logger.warning(f"{provider.name} failed ({e}), trying next provider...")
            last_error = e
            continue
    else:
        # All providers failed
        return {
            "tool_calls": [],
            "message": (
                "### AI Execution Failure\n\n"
                f"All configured AI providers failed to execute your request. Last error details: `{last_error}`. "
                "Please verify your API credentials in the **Settings** view."
            )
        }

    try:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        json_str = _sanitize_llm_json(json_str)

        parsed = json.loads(json_str)

        # Remap 'parameters' -> 'args' inside each tool_call (common LLM alias)
        for call in parsed.get("tool_calls", []):
            if "parameters" in call and "args" not in call:
                call["args"] = call.pop("parameters")

        # Validate structure with Pydantic
        validated = AgentResponse(**parsed)
        return validated.model_dump()
    except Exception as e:
        logger.error(f"Format error in agent response parsing: {e}. Raw response: {response}")
        return {
            "tool_calls": [],
            "message": f"Response could not be parsed as structured JSON. Details: {e}\nRaw: {response}"
        }


agent = PlaxisAgentSwarm()
