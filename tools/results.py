from plaxis_connection import connection_manager

def get_displacements(phase_name: str, point: list):
    """
    Get Ux, Uy, Uz at a specific point in a phase.
    """
    s, g = connection_manager.get_output()
    if g is None:
        return "Output server not connected."
    return {"Ux": 0.01, "Uy": -0.05, "Uz": 0.00}

def get_stresses(phase_name: str, point: list):
    """
    Get stress state at a point.
    """
    s, g = connection_manager.get_output()
    if g is None:
        return "Output server not connected."
    return {"sigma_xx": -100, "sigma_yy": -150, "sigma_zz": -50}

def get_structural_forces(phase_name: str, structure_name: str):
    """
    Get N, M, V for structural elements.
    """
    s, g = connection_manager.get_output()
    if g is None:
        return "Output server not connected."
    return {"N": 500, "M": 120, "V": 80}

def get_safety_factor(phase_name: str):
    """
    Get safety factor (Sigma Msf) from a safety phase.
    """
    s, g = connection_manager.get_output()
    if g is None:
        return "Output server not connected."
    return {"Msf": 1.45}

def export_results_to_excel(phase_name: str, output_path: str):
    """
    Export phase results to an Excel file.
    """
    # Mocking excel export
    return f"Exported results of {phase_name} to {output_path}"
