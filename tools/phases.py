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

def add_phase(name: str, phase_type: str = "Plastic"):
    """
    Add a new calculation phase.

    Args:
        name (str): Display name for the phase.
        phase_type (str): 'Initial', 'Plastic', 'Consolidation', 'Safety', 'Dynamic'.
    """
    s, g = connection_manager.get_input()
    
    phase = g.phase(g.Phases[-1])  # Add after the last existing phase
    phase.Identification = name
    
    # Set calculation type
    pt = phase_type.strip().lower()
    if pt in PHASE_TYPE_MAP:
        phase.DeformCalcType = PHASE_TYPE_MAP[pt]
    
    return f"Added phase '{name}' of type '{phase_type}'."

def activate(phase_name: str, object_name: str):
    """
    Activate an object in a specific phase.

    Args:
        phase_name (str): Name of the phase (e.g., 'Phase_1').
        object_name (str): Name of the object to activate.
    """
    s, g = connection_manager.get_input()
    phase = connection_manager.find_object_by_name(phase_name)
    obj = connection_manager.find_object_by_name(object_name)
    g.activate(obj, phase)
    return f"Activated '{object_name}' in '{phase_name}'."

def deactivate(phase_name: str, object_name: str):
    """
    Deactivate an object in a phase (e.g., for excavation simulation).

    Args:
        phase_name (str): Name of the phase.
        object_name (str): Name of the object to deactivate.
    """
    s, g = connection_manager.get_input()
    phase = connection_manager.find_object_by_name(phase_name)
    obj = connection_manager.find_object_by_name(object_name)
    g.deactivate(obj, phase)
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
    
    # Set water conditions for this phase
    phase.WaterLevel = level
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
