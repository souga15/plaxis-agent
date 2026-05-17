from plaxis_connection import connection_manager

def create_soil_material(name: str, model: str, params: dict):
    """
    Create a soil material.
    
    Args:
        name (str): Material name.
        model (str): Soil model (e.g., 'Mohr-Coulomb', 'Hardening Soil').
        params (dict): Dictionary of parameters (gammaUnsat, gammaSat, E, nu, etc.)
    """
    s, g = connection_manager.get_input()
    mat = g.soilmat('MaterialName', name, 'SoilModel', model)
    for key, val in params.items():
        mat.set(key, val)
    return f"Created soil material '{name}'."

def create_plate_material(name: str, params: dict):
    """
    Create a plate material.
    """
    s, g = connection_manager.get_input()
    mat = g.platemat('MaterialName', name)
    for key, val in params.items():
        mat.set(key, val)
    return f"Created plate material '{name}'."

def create_anchor_material(name: str, params: dict):
    """
    Create an anchor material.
    """
    s, g = connection_manager.get_input()
    mat = g.anchormat('MaterialName', name)
    for key, val in params.items():
        mat.set(key, val)
    return f"Created anchor material '{name}'."

def assign_material(object_name: str, material_name: str):
    """
    Assign a material to an object.
    """
    s, g = connection_manager.get_input()
    obj = getattr(g, object_name)
    mat = getattr(g, material_name)
    obj.setmaterial(mat)
    return f"Assigned '{material_name}' to '{object_name}'."
