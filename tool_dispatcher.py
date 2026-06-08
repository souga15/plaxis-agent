"""
Tool Dispatcher — Maps LLM tool_call names to actual Python functions
and executes them with the provided arguments against the live Plaxis instance.
"""

import logging
from plaxis_connection import connection_manager
from tools import geometry, materials, structures, mesh, phases, calculate, results, project

logger = logging.getLogger(__name__)

PROJECT_BOOTSTRAP_TOOLS = {"new_project", "open_project"}
PROJECT_DEPENDENT_TOOLS = {
    "create_borehole",
    "create_polygon",
    "create_line",
    "create_surface",
    "create_volume",
    "extrude",
    "create_soil_material",
    "create_plate_material",
    "create_anchor_material",
    "assign_material",
    "create_plate",
    "create_anchor",
    "create_pile",
    "create_interface",
    "create_load",
}

# Registry: tool name -> callable
TOOL_REGISTRY = {
    # Geometry
    "create_borehole": geometry.create_borehole,
    "create_polygon": geometry.create_polygon,
    "create_line": geometry.create_line,
    "create_surface": geometry.create_surface,
    "create_volume": geometry.create_volume,
    "extrude": geometry.extrude,
    "find_object_by_coordinates": geometry.find_object_by_coordinates,

    # Materials
    "create_soil_material": materials.create_soil_material,
    "create_plate_material": materials.create_plate_material,
    "create_anchor_material": materials.create_anchor_material,
    "assign_material": materials.assign_material,

    # Structures
    "create_plate": structures.create_plate,
    "create_anchor": structures.create_anchor,
    "create_pile": structures.create_pile,
    "create_interface": structures.create_interface,
    "create_load": structures.create_load,

    # Mesh
    "generate_mesh": mesh.generate_mesh,
    "refine_mesh_around": mesh.refine_mesh_around,
    "get_mesh_quality": mesh.get_mesh_quality,

    # Phases
    "add_phase": phases.add_phase,
    "activate": phases.activate,
    "deactivate": phases.deactivate,
    "set_water_level": phases.set_water_level,
    "list_phases": phases.list_phases,

    # Calculation
    "run_calculation": calculate.run_calculation,
    "get_calculation_status": calculate.get_calculation_status,
    "get_log": calculate.get_log,

    # Results
    "get_displacements": results.get_displacements,
    "get_stresses": results.get_stresses,
    "get_structural_forces": results.get_structural_forces,
    "get_safety_factor": results.get_safety_factor,
    "export_results_to_excel": results.export_results_to_excel,

    # Project
    "new_project": project.new_project,
    "open_project": project.open_project,
    "save_project": project.save_project,
    "close_project": project.close_project,
}

# Aliases for common LLM hallucinations / deprecated names -> canonical tool names
TOOL_ALIASES = {
    "create_material": "create_soil_material",
    "add_borehole": "create_borehole",
    "evaluate_design_safety": "get_safety_factor",
    "check_safety": "get_safety_factor",
    "get_factor_of_safety": "get_safety_factor",
    "add_calculation_phase": "add_phase",
    "create_phase": "add_phase",
    "mesh": "generate_mesh",
    "set_material": "assign_material",
    "soilmat": "create_soil_material",
}


def _execute_tool_call(call: dict) -> dict:
    tool_name = call.get("name", "unknown")
    tool_args = dict(call.get("args", {}))

    # Silently remap deprecated or hallucinated tool names
    if tool_name in TOOL_ALIASES:
        original_name = tool_name
        tool_name = TOOL_ALIASES[tool_name]
        logger.warning(f"Tool alias: '{original_name}' -> '{tool_name}'")

    if tool_name not in TOOL_REGISTRY:
        return {
            "tool": tool_name,
            "success": False,
            "result": f"Unknown tool '{tool_name}'. Available: {list(TOOL_REGISTRY.keys())}"
        }

    # Preprocess arguments to handle common LLM calling discrepancies
    if tool_name == "create_soil_material":
        name = tool_args.get("name")
        model = tool_args.get("model")
        # Accept both 'params' and 'parameters' as the dict key
        params = tool_args.get("params") or tool_args.get("parameters") or {}
        if not isinstance(params, dict):
            params = {}
        # Extract any other top-level keys into params
        for k, v in list(tool_args.items()):
            if k not in {"name", "model", "params", "parameters"}:
                params[k] = v
        tool_args = {"name": name, "model": model, "params": params}

    elif tool_name == "assign_material":
        object_name = tool_args.get("object_name")
        if object_name is None:
            object_name = (tool_args.get("layer_name") or tool_args.get("object")
                           or tool_args.get("target") or tool_args.get("borehole"))
        # Convert integer layer index -> "Soillayer_N" (LLM sometimes passes 1, 2, ...)
        if isinstance(object_name, int):
            object_name = f"Soillayer_{object_name}"
        elif isinstance(object_name, str) and object_name.isdigit():
            object_name = f"Soillayer_{object_name}"
        material_name = tool_args.get("material_name")
        if material_name is None:
            # LLM sometimes passes the material name as 'name' in assign_material
            material_name = (tool_args.get("materials") or tool_args.get("material")
                             or tool_args.get("mat") or tool_args.get("name"))
        tool_args = {"object_name": object_name, "material_name": material_name}

    elif tool_name == "create_borehole":
        if "point" in tool_args:
            pt = tool_args.pop("point")
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                tool_args["x"] = pt[0]
                tool_args["y"] = pt[1]
            elif isinstance(pt, dict):
                tool_args["x"] = pt.get("x", 0.0)
                tool_args["y"] = pt.get("y", 0.0)
        # Ensure x and y are present
        if "x" not in tool_args:
            tool_args["x"] = 0.0
        if "y" not in tool_args:
            tool_args["y"] = 0.0
        # Decode layers if LLM passed it as a JSON string
        layers = tool_args.get("layers", [])
        if isinstance(layers, str):
            import json as _json
            try:
                layers = _json.loads(layers)
            except Exception:
                layers = []
        # Normalize layers: [[top, bottom], ...] -> [{"top": t, "bottom": b}, ...]
        if layers and isinstance(layers[0], (list, tuple)):
            layers = [{"top": item[0], "bottom": item[1]} for item in layers if len(item) >= 2]
        tool_args["layers"] = layers

    try:
        func = TOOL_REGISTRY[tool_name]
        result = func(**tool_args)
        logger.info(f"Tool '{tool_name}' executed successfully: {result}")
        return {
            "tool": tool_name,
            "success": True,
            "result": str(result),
            "raw_result": result
        }
    except Exception as e:
        logger.error(f"Tool '{tool_name}' failed: {e}")
        compatibility_message = connection_manager.classify_runtime_issue(e)
        return {
            "tool": tool_name,
            "success": False,
            "result": compatibility_message or f"Error: {str(e)}",
            "compatibility_issue": compatibility_message is not None,
        }


def _should_retry_with_new_project(tool_calls: list, failed_call: dict, failure_result: dict) -> bool:
    if any(call.get("name") in PROJECT_BOOTSTRAP_TOOLS for call in tool_calls):
        return False
    if failed_call.get("name") not in PROJECT_DEPENDENT_TOOLS:
        return False

    result_text = failure_result.get("result", "").lower()
    return "is not recognized as a global command" in result_text


def dispatch_tool_calls(tool_calls: list, allow_project_bootstrap: bool = True) -> list:
    """
    Execute a list of tool calls from the LLM and return results.
    
    Args:
        tool_calls: List of dicts, each with 'name' and 'args' keys.
                    Example: [{"name": "create_borehole", "args": {"x": 0, "y": 0, "layers": []}}]
    
    Returns:
        List of result dicts with 'tool', 'success', and 'result' keys.
    """
    execution_results = []

    for call in tool_calls:
        result = _execute_tool_call(call)
        execution_results.append(result)

        if allow_project_bootstrap and not result["success"] and _should_retry_with_new_project(tool_calls, call, result):
            logger.warning(
                "Detected PLAXIS start-page style failure for '%s'. "
                "Attempting automatic new_project() bootstrap and retrying the batch once.",
                call.get("name", "unknown"),
            )
            project_result = _execute_tool_call({"name": "new_project", "args": {}})
            if project_result["success"]:
                project_result["result"] += " Auto-recovery: started a new project after blank-session command failure."
                return [project_result] + dispatch_tool_calls(tool_calls, allow_project_bootstrap=False)
            project_result["result"] += " Auto-recovery failed while trying to create a project automatically."
            execution_results.append(project_result)
            return execution_results

    return execution_results
