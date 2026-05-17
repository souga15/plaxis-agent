import logging
import re
from plaxis_connection import connection_manager

logger = logging.getLogger(__name__)


def _plaxis_literal(value):
    if isinstance(value, str):
        return '"' + value.replace('"', '\\"') + '"'
    return str(value)

# Plaxis SoilModel enum values
SOIL_MODEL_MAP = {
    "linear elastic": 1,
    "mohr-coulomb": 2,
    "hardening soil": 3,
    "hardening soil small": 4,
    "soft soil": 5,
    "soft soil creep": 6,
    "jointed rock": 7,
    "modified cam-clay": 8,
    "ngi-adp": 9,
    "sekiguchi-ohta": 10,
    "hoek-brown": 11,
}

def _resolve_soil_model(model: str) -> int:
    """Convert a soil model name string to its Plaxis enum integer."""
    key = model.strip().lower().replace("_", " ").replace("-", " ")
    # Normalize map keys the same way so hyphens in canonical names
    # (e.g. "ngi-adp", "hoek-brown") don't cause mismatches.
    normalized_map = {k.replace("-", " "): v for k, v in SOIL_MODEL_MAP.items()}
    if key in normalized_map:
        return normalized_map[key]
    # Try partial match
    for name, val in normalized_map.items():
        if key in name or name in key:
            return val
    # Default to Mohr-Coulomb if unrecognized
    logger.warning(f"Unknown soil model '{model}', defaulting to Mohr-Coulomb (2)")
    return 2

def create_soil_material(name: str, model: str, params: dict):
    """
    Create a soil material.

    Args:
        name (str): Material name.
        model (str): Soil model name (e.g., 'Mohr-Coulomb', 'Hardening Soil').
        params (dict): Dictionary of parameters (gammaUnsat, gammaSat, E, nu, cref, phi, etc.)
    """
    s, g = connection_manager.get_input()

    try:
        # Preferred wrapper path when available.
        mat = g.soilmat()
        props = ["Identification", name, "SoilModel", _resolve_soil_model(model)]
        for key, val in params.items():
            props.append(key)
            props.append(val)
        mat.setproperties(*props)
    except Exception as e:
        logger.warning(f"Wrapper soilmat() unavailable, falling back to native command: {e}")
        tokens = ["soilmat", _plaxis_literal("Identification"), _plaxis_literal(name), _plaxis_literal("SoilModel"), _plaxis_literal(model)]
        for key, val in params.items():
            tokens.append(_plaxis_literal(key))
            tokens.append(_plaxis_literal(val))
        connection_manager.call_command(" ".join(tokens), server="input")

    return f"Created soil material '{name}' with model '{model}'."

def create_plate_material(name: str, params: dict):
    """
    Create a plate material.
    
    Args:
        name (str): Material name.
        params (dict): Properties like d (thickness), E1, E2, nu12, etc.
    """
    s, g = connection_manager.get_input()
    mat = g.platemat()
    
    props = ["MaterialName", name]
    for key, val in params.items():
        props.append(key)
        props.append(val)
    
    mat.setproperties(*props)
    return f"Created plate material '{name}'."

def create_anchor_material(name: str, params: dict):
    """
    Create an anchor material.
    
    Args:
        name (str): Material name.
        params (dict): Properties like EA, Lspacing, etc.
    """
    s, g = connection_manager.get_input()
    mat = g.anchormat()
    
    props = ["MaterialName", name]
    for key, val in params.items():
        props.append(key)
        props.append(val)
    
    mat.setproperties(*props)
    return f"Created anchor material '{name}'."

def assign_material(object_name: str, material_name: str):
    """
    Assign a material to an object.
    
    Args:
        object_name (str): Name of the target object (e.g., 'SoilLayer_1', 'Plate_1').
        material_name (str): Name of the material to assign.
    """
    s, g = connection_manager.get_input()
    mat = connection_manager.find_object_by_name(material_name)

    try:
        obj = connection_manager.find_object_by_name(object_name)
        g.setmaterial(obj, mat)
        return f"Assigned '{material_name}' to '{object_name}'."
    except ValueError:
        pass

    match = re.fullmatch(r"(?:soil|soillayer)[_\s]*(\d+)", object_name.strip(), flags=re.IGNORECASE)
    if match:
        layer_index = int(match.group(1)) - 1
        if 0 <= layer_index < len(g.Soillayers):
            g.setmaterial(g.Soillayers[layer_index], mat)
            layer_name = connection_manager._safe_attr(g.Soillayers[layer_index], "Name") or f"Soillayer_{layer_index + 1}"
            return f"Assigned '{material_name}' to '{layer_name}'."

    obj = connection_manager.find_object_by_name(object_name)
    g.setmaterial(obj, mat)
    return f"Assigned '{material_name}' to '{object_name}'."
