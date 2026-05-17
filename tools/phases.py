import logging
from plaxis_connection import connection_manager

logger = logging.getLogger(__name__)

# Plaxis phase type mapping
PHASE_TYPE_MAP = {
    "initial": "InitialPhase",
    "plastic": "Plastic",
    "consolidation": "Consolidation",
    "safety": "Safety",
    "dynamic": "Dynamic",
    "flow only": "FlowOnly",
    "fully coupled": "FullyCoupled",
}


def _safe_value(obj, attr_name: str, default=None):
    try:
        value = getattr(obj, attr_name, default)
        return value.value if hasattr(value, "value") else value
    except Exception:
        return default


def _goto_stages_mode(g):
    try:
        g.gotostages()
        return
    except Exception as e:
        logger.warning(f"Wrapper gotostages() unavailable, falling back to native command: {e}")
    try:
        connection_manager.call_command("gotostages", server="input")
    except Exception as e:
        logger.warning(f"Native command gotostages is unavailable in this PLAXIS build: {e}")

def add_phase(name: str, phase_type: str = "Plastic"):
    """
    Add a new calculation phase.

    Args:
        name (str): Display name for the phase.
        phase_type (str): 'Initial', 'Plastic', 'Consolidation', 'Safety', 'Dynamic'.
    """
    s, g = connection_manager.get_input()
    _goto_stages_mode(g)

    try:
        phase = g.phase(g.Phases[-1])  # Add after the last existing phase
    except Exception as e:
        logger.warning(f"Wrapper phase() unavailable, falling back to native command: {e}")
        previous_phase = g.Phases[-1]
        previous_name = _safe_value(previous_phase, "Name") or _safe_value(previous_phase, "Identification") or "InitialPhase"
        connection_manager.call_command(f"phase {previous_name}", server="input")
        phase = g.Phases[-1]

    try:
        phase.Identification = name
    except Exception as e:
        logger.warning(f"Direct phase identification assignment failed, falling back to native command: {e}")
        phase_name = _safe_value(phase, "Name") or "Phase_1"
        connection_manager.call_command(f'set {phase_name}.Identification "{name}"', server="input")

    pt = phase_type.strip().lower()
    if pt in PHASE_TYPE_MAP:
        try:
            phase.DeformCalcType = PHASE_TYPE_MAP[pt]
        except Exception as e:
            logger.warning(f"Direct phase type assignment failed, falling back to native command: {e}")
            phase_name = _safe_value(phase, "Name") or "Phase_1"
            connection_manager.call_command(
                f'set {phase_name}.DeformCalcType "{PHASE_TYPE_MAP[pt]}"',
                server="input",
            )
    
    return f"Added phase '{name}' of type '{phase_type}'."

def activate(phase_name: str, object_name: str):
    """
    Activate an object in a specific phase.

    Args:
        phase_name (str): Name of the phase (e.g., 'Phase_1').
        object_name (str): Name of the object to activate.
    """
    s, g = connection_manager.get_input()
    _goto_stages_mode(g)
    phase = connection_manager.find_object_by_name(phase_name)
    obj = connection_manager.find_object_by_name(object_name)
    try:
        g.activate(obj, phase)
    except Exception as e:
        logger.warning(f"Wrapper activate() unavailable, falling back to native command: {e}")
        obj_name = _safe_value(obj, "Name") or object_name
        phase_obj_name = _safe_value(phase, "Name") or phase_name
        connection_manager.call_command(f"activate {obj_name} {phase_obj_name}", server="input")
    return f"Activated '{object_name}' in '{phase_name}'."

def deactivate(phase_name: str, object_name: str):
    """
    Deactivate an object in a phase (e.g., for excavation simulation).

    Args:
        phase_name (str): Name of the phase.
        object_name (str): Name of the object to deactivate.
    """
    s, g = connection_manager.get_input()
    _goto_stages_mode(g)
    phase = connection_manager.find_object_by_name(phase_name)
    obj = connection_manager.find_object_by_name(object_name)
    try:
        g.deactivate(obj, phase)
    except Exception as e:
        logger.warning(f"Wrapper deactivate() unavailable, falling back to native command: {e}")
        obj_name = _safe_value(obj, "Name") or object_name
        phase_obj_name = _safe_value(phase, "Name") or phase_name
        connection_manager.call_command(f"deactivate {obj_name} {phase_obj_name}", server="input")
    return f"Deactivated '{object_name}' in '{phase_name}'."

def set_water_level(phase_name: str, level: float):
    """
    Set the global water level for a phase.

    Args:
        phase_name (str): Name of the phase.
        level (float): Water level elevation (negative = below surface).
    """
    s, g = connection_manager.get_input()
    phase = connection_manager.find_object_by_name(phase_name)
    
    try:
        phase.WaterLevel = level
    except Exception as e:
        logger.warning(f"Wrapper WaterLevel unavailable, falling back to native command: {e}")
        phase_obj_name = _safe_value(phase, "Name") or phase_name
        connection_manager.call_command(f"set {phase_obj_name}.WaterLevel {level}", server="input")
        
    return f"Set water level to {level}m in '{phase_name}'."

def list_phases():
    """
    List all defined calculation phases with their types and status.
    """
    s, g = connection_manager.get_input()
    phases = []
    try:
        for p in g.Phases:
            try:
                phase_info = {
                    "name": p.Name.value if hasattr(p.Name, 'value') else str(p.Name),
                    "identification": p.Identification.value if hasattr(p.Identification, 'value') else str(p.Identification),
                }
                phases.append(phase_info)
            except Exception:
                phases.append({"name": str(p)})
    except Exception as e:
        logger.warning(f"Could not list phases: {e}")
    
    return {"phases": phases, "count": len(phases)}
