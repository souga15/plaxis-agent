import json
import logging
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any
from providers.gemini import GeminiProvider
from providers.groq import GroqProvider

logger = logging.getLogger(__name__)

class ToolCall(BaseModel):
    name: str = Field(..., description="Name of the tool to execute")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool")

class AgentResponse(BaseModel):
    tool_calls: List[ToolCall] = Field(default_factory=list)
    message: str = Field(..., description="Message explaining what actions were taken by this agent")


class GeometryAgent:
    def __init__(self, gemini, groq):
        self.gemini = gemini
        self.groq = groq
        self.system_prompt = """
You are the Geotechnical Geometry Agent.
Your job is to read the user's design constraints and any feedback, then generate structural, material, or coordinate layout tool calls.
You only focus on geometry, boreholes, soils, and physical objects.

=== AVAILABLE GEOMETRY & MATERIAL TOOLS ===
- create_borehole(x: float, y: float, layers: list)
    layers = [{"top": 0, "bottom": -5}, {"top": -5, "bottom": -15}]
- create_surface(points: list)
    points = [x1,y1,z1, x2,y2,z2, ...] or [[x1,y1,z1], [x2,y2,z2], ...]
- create_volume(points: list)  — ONLY takes 'points', no other arguments.
- extrude(object_name: str, direction: list, length: float)
- find_object_by_coordinates(x: float, y: float, z: float, collection: str)
- create_soil_material(name: str, model: str, params: dict)
    model: "Mohr-Coulomb", "Hardening Soil", "Soft Soil", "Linear Elastic"
    params: {"gammaUnsat": 18, "gammaSat": 20, "Eref": 30000, "nu": 0.3, "cref": 10, "phi": 25}
- create_plate_material(name: str, params: dict)
    params: {"d": 0.5, "E1": 30e6, "nu12": 0.15, "w": 12.0}
- create_anchor_material(name: str, params: dict)
- assign_material(object_name: str, material_name: str)
- create_plate(points: list)
- create_anchor(point1: list, point2: list)
- create_pile(point: list, depth: float)
- create_interface(object_name: str)
- create_load(load_type: str, points: list, value: list)

=== RESPONSE FORMAT ===
You MUST respond with a valid JSON block containing "tool_calls" and "message".
If the design is already created or no geometric changes are needed, return an empty tool_calls list.
Always create materials before assigning them.
"""

    async def execute(self, user_prompt: str, design_feedback: str = ""):
        prompt = f"User Request: {user_prompt}\n"
        if design_feedback:
            prompt += f"\nDesign Validation Feedback to address: {design_feedback}\n"
        
        logger.info("[Swarm] Invoking GeometryAgent...")
        return await _call_llm(self.gemini, self.groq, self.system_prompt, prompt)


class CalculationAgent:
    def __init__(self, gemini, groq):
        self.gemini = gemini
        self.groq = groq
        self.system_prompt = """
You are the Solver and Calculation Agent.
Your job is to read the active design state, create mesh parameters, define calculation phases, activate/deactivate structural elements, and run calculations.

=== AVAILABLE CALCULATION & MESH TOOLS ===
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
You MUST respond with a valid JSON block containing "tool_calls" and "message".
Remember to generate the mesh before running the calculation!
"""

    async def execute(self, user_prompt: str, geometry_log: str):
        prompt = f"User Request: {user_prompt}\n\nGeometry Actions Completed:\n{geometry_log}"
        logger.info("[Swarm] Invoking CalculationAgent...")
        return await _call_llm(self.gemini, self.groq, self.system_prompt, prompt)


class ValidationAgent:
    def __init__(self, gemini, groq):
        self.gemini = gemini
        self.groq = groq
        self.system_prompt = """
You are the Extraction and Validation Agent.
Your job is to query phase results (stresses, displacements, structural envelope forces, and factor of safety Msf) and verify if the design is completely safe.

=== AVAILABLE RESULTS TOOLS ===
- get_displacements(phase_name: str, point: list)
- get_stresses(phase_name: str, point: list)
- get_structural_forces(phase_name: str, structure_name: str)
- get_safety_factor(phase_name: str)
- export_results_to_excel(phase_name: str, output_path: str)

=== RESPONSE FORMAT ===
You MUST respond with a valid JSON block containing "tool_calls" and "message".
Make sure to call `get_safety_factor` for any safety phase (e.g. Phase_2 or Phase_3) to evaluate Sum-Msf!
"""

    async def execute(self, user_prompt: str, workflow_log: str):
        prompt = f"User Request: {user_prompt}\n\nWorkflow Execution Progress:\n{workflow_log}"
        logger.info("[Swarm] Invoking ValidationAgent...")
        return await _call_llm(self.gemini, self.groq, self.system_prompt, prompt)


class PlaxisAgentSwarm:
    def __init__(self):
        self.gemini = GeminiProvider()
        self.groq = GroqProvider()
        self.geometry_agent = GeometryAgent(self.gemini, self.groq)
        self.calculation_agent = CalculationAgent(self.gemini, self.groq)
        self.validation_agent = ValidationAgent(self.gemini, self.groq)

    async def process_request(self, user_prompt: str):
        """
        Orchestrates the linear multi-agent swarm pipeline:
        Geometry Agent -> Calculation Agent -> Validation Agent.
        If validation shows Safety Factor < 1.25, triggers a feedback loop.
        """
        from tool_dispatcher import dispatch_tool_calls

        swarm_logs = []
        design_feedback = ""
        max_cycles = 2

        for cycle in range(max_cycles):
            cycle_prefix = f"### 🔄 Design Optimization Cycle {cycle + 1}/{max_cycles}\n"
            swarm_logs.append(cycle_prefix)

            # ---------------------------------------------
            # STEP 1: Geotechnical Geometry Agent
            # ---------------------------------------------
            geo_response = await self.geometry_agent.execute(user_prompt, design_feedback)
            swarm_logs.append(f"🤖 **[Geotechnical Geometry Agent]**:\n{geo_response['message']}")
            
            geo_calls = geo_response.get("tool_calls", [])
            if geo_calls:
                geo_results = dispatch_tool_calls(geo_calls)
                exec_log = "\n".join([f"✅ `{r['tool']}`: {r['result']}" if r["success"] else f"❌ `{r['tool']}`: {r['result']}" for r in geo_results])
                swarm_logs.append(f"📋 **Geometry Execution Results:**\n{exec_log}")
                geo_log_str = "\n".join([f"- {r['tool']}: Success={r['success']}, Output={r['result']}" for r in geo_results])
            else:
                geo_log_str = "No geometry updates required."
                swarm_logs.append("📋 *No geometry actions proposed.*")
            
            # ---------------------------------------------
            # STEP 2: Solver & Calculation Agent
            # ---------------------------------------------
            calc_response = await self.calculation_agent.execute(user_prompt, geo_log_str)
            swarm_logs.append(f"⚙️ **[Solver & Calculation Agent]**:\n{calc_response['message']}")
            
            calc_calls = calc_response.get("tool_calls", [])
            if calc_calls:
                calc_results = dispatch_tool_calls(calc_calls)
                exec_log = "\n".join([f"✅ `{r['tool']}`: {r['result']}" if r["success"] else f"❌ `{r['tool']}`: {r['result']}" for r in calc_results])
                swarm_logs.append(f"📋 **Calculation Execution Results:**\n{exec_log}")
                calc_log_str = "\n".join([f"- {r['tool']}: Success={r['success']}, Output={r['result']}" for r in calc_results])
            else:
                calc_log_str = "No calculation actions required."
                swarm_logs.append("📋 *No calculation actions proposed.*")

            # ---------------------------------------------
            # STEP 3: Extraction & Validation Agent
            # ---------------------------------------------
            combined_progress = f"--- Geometry Phase ---\n{geo_log_str}\n\n--- Calculation Phase ---\n{calc_log_str}"
            val_response = await self.validation_agent.execute(user_prompt, combined_progress)
            swarm_logs.append(f"🔍 **[Extraction & Validation Agent]**:\n{val_response['message']}")
            
            val_calls = val_response.get("tool_calls", [])
            safety_factor = None
            if val_calls:
                val_results = dispatch_tool_calls(val_calls)
                exec_log = "\n".join([f"✅ `{r['tool']}`: {r['result']}" if r["success"] else f"❌ `{r['tool']}`: {r['result']}" for r in val_results])
                swarm_logs.append(f"📋 **Extraction Results:**\n{exec_log}")
                
                # Check for get_safety_factor output
                for r in val_results:
                    if r["tool"] == "get_safety_factor" and r["success"]:
                        raw = r.get("raw_result")
                        if isinstance(raw, dict) and "safety_factor" in raw:
                            val = raw["safety_factor"]
                            if isinstance(val, (int, float)):
                                safety_factor = val
            else:
                swarm_logs.append("📋 *No result extraction actions proposed.*")

            # ---------------------------------------------
            # STEP 4: Safety Check & Feedback Loop
            # ---------------------------------------------
            if safety_factor is not None:
                swarm_logs.append(f"📊 **[Safety Review]**: Current Safety Factor (Sum-Msf) = **{safety_factor:.3f}** (Target: **1.25**)")
                if safety_factor < 1.25:
                    if cycle < max_cycles - 1:
                        design_feedback = (
                            f"Safety evaluation FAILED. The computed Safety Factor (Sum-Msf) is {safety_factor:.3f}, "
                            f"which is below our engineering threshold of 1.25. "
                            f"Geometry Agent, please redesign the structure to increase stability (e.g. increase wall thickness, "
                            f"deepen piles, or modify anchor stiffness)."
                        )
                        swarm_logs.append(f"⚠️ **[Feedback Loop Triggered]**: Safety factor below target. Instructing Geometry Agent to strengthen the model and recalculate...")
                        swarm_logs.append("\n" + "="*40 + "\n")
                        continue
                    else:
                        swarm_logs.append(f"🛑 **[Verification End]**: Design remains under-safe after maximum optimization cycles.")
                else:
                    swarm_logs.append(f"✅ **[Verification Success]**: Design meets the target safety margin ($FoS \\ge 1.25$). Optimization complete.")
                    break
            else:
                # No safety factor retrieved, complete execution
                break

        return {
            "tool_calls": [],  # Swarm executed tools internally
            "message": "\n\n".join(swarm_logs)
        }


async def _call_llm(gemini, groq, system_prompt: str, prompt: str) -> dict:
    try:
        response = await gemini.generate_response(system_prompt, prompt)
    except Exception as e:
        logger.warning(f"Gemini failed ({e}), falling back to Groq...")
        response = await groq.generate_response(system_prompt, prompt)

    try:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        parsed = json.loads(json_str)
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
