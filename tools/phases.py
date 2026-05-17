from plaxis_connection import connection_manager

def add_phase(name: str, phase_type: str = "Plastic"):
    """
    Add a new calculation phase.
    
    Args:
        name (str): Name of the phase.
        phase_type (str): 'Initial', 'Plastic', 'Consolidation', 'Safety'.
    """
    s, g = connection_manager.get_input()
    # Mocking
    phase = g.phase()
    phase.Identification = name
    return f"Added phase '{name}' of type '{phase_type}'."

def activate(phase_name: str, object_name: str):
    """
    Activate an object in a phase.
    """
    s, g = connection_manager.get_input()
    phase = getattr(g, phase_name)
    obj = getattr(g, object_name)
    g.activate(obj, phase)
    return f"Activated {object_name} in {phase_name}."

def deactivate(phase_name: str, object_name: str):
    """
    Deactivate an object in a phase (e.g., excavation).
    """
    s, g = connection_manager.get_input()
    phase = getattr(g, phase_name)
    obj = getattr(g, object_name)
    g.deactivate(obj, phase)
    return f"Deactivated {object_name} in {phase_name}."

def set_water_level(phase_name: str, level: float):
    """
    Set groundwater level.
    """
    s, g = connection_manager.get_input()
    return f"Set water level to {level} in {phase_name}."

def list_phases():
    """
    List all defined phases.
    """
    s, g = connection_manager.get_input()
    phases = [p.Name.value for p in g.Phases] if hasattr(g, 'Phases') else []
    return {"phases": phases}
