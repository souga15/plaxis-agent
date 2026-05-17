"""
Tool Dispatcher — Maps LLM tool_call names to actual Python functions
and executes them with the provided arguments against the live Plaxis instance.
"""

import logging
from plaxis_connection import connection_manager
from tools import geometry, materials, structures, mesh, phases, calculate, results, project

logger = logging.getLogger(__name__)

# Registry: tool name -> callable
TOOL_REGISTRY = {
    # Geometry
    "create_borehole": geometry.create_borehole,
    "create_surface": geometry.create_surface,
    "create_volume": geometry.create_volume,
    "extrude": geometry.extrude,

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


def dispatch_tool_calls(tool_calls: list) -> list:
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
        tool_name = call.get("name", "unknown")
        tool_args = call.get("args", {})

        if tool_name not in TOOL_REGISTRY:
            execution_results.append({
                "tool": tool_name,
                "success": False,
                "result": f"Unknown tool '{tool_name}'. Available: {list(TOOL_REGISTRY.keys())}"
            })
            continue

        try:
            func = TOOL_REGISTRY[tool_name]
            result = func(**tool_args)
            logger.info(f"Tool '{tool_name}' executed successfully: {result}")
            execution_results.append({
                "tool": tool_name,
                "success": True,
                "result": str(result)
            })
        except Exception as e:
            logger.error(f"Tool '{tool_name}' failed: {e}")
            compatibility_message = connection_manager.classify_runtime_issue(e)
            execution_results.append({
                "tool": tool_name,
                "success": False,
                "result": compatibility_message or f"Error: {str(e)}",
                "compatibility_issue": compatibility_message is not None,
            })

    return execution_results
