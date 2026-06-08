import logging
import re
from plaxis_connection import connection_manager

logger = logging.getLogger(__name__)


def _plaxis_literal(value):
    if isinstance(value, str):
        return '"' + value.replace('"', '\\"') + '"'
    return str(value)


def _goto_soil_mode(g):
    try:
        g.gotosoil()
        return
    except Exception as e:
        logger.warning(f"Wrapper gotosoil() unavailable, falling back to native command: {e}")
    try:
        connection_manager.call_command("gotosoil", server="input")
    except Exception as e:
        logger.warning(f"Native command gotosoil is unavailable in this PLAXIS build: {e}")

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
    _goto_soil_mode(g)

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
        object_name (str): Name of the target object (e.g., 'Soillayer_1', 'Plate_1').
                           Pass None or 'all' to assign to every soil layer.
        material_name (str): Name of the material to assign.
    """
    s, g = connection_manager.get_input()
    _goto_soil_mode(g)

    # Resolve the material object — look up by name first, then fall back to
    # using the name string directly in native commands.
    mat = None
    mat_obj_name = material_name  # default: use the string name in commands
    try:
        mat = connection_manager.find_object_by_name(material_name)
        mat_obj_name = connection_manager._safe_attr(mat, "Name") or material_name
    except ValueError:
        logger.warning(f"Material '{material_name}' not found as object; will use name string in commands.")

    # ── Helper: assign to a single Soillayer object ──────────────────────────
    def _assign_to_layer(layer_obj, layer_label: str) -> str:
        layer_name = connection_manager._safe_attr(layer_obj, "Name") or layer_label
        # Primary path: native `set` command  (matches recorded CLI: _set Soillayer_1.Soil.Material SoilMat_1)
        try:
            connection_manager.call_command(
                f"set {layer_name}.Soil.Material {mat_obj_name}", server="input"
            )
            return f"Assigned '{material_name}' to '{layer_name}'."
        except Exception as e1:
            logger.warning(f"Native set command failed ({e1}), trying direct attribute assignment.")
        # Secondary path: direct Python attribute
        try:
            if mat is not None:
                layer_obj.Soil.Material = mat
            return f"Assigned '{material_name}' to '{layer_name}'."
        except Exception as e2:
            logger.warning(f"Direct attribute assignment failed ({e2}), trying g.setmaterial().")
        # Tertiary path: wrapper API
        if mat is not None:
            g.setmaterial(layer_obj, mat)
        return f"Assigned '{material_name}' to '{layer_name}'."

    # ── If caller passes None / 'all' / 'borehole' / empty → assign to ALL layers ──
    generic_names = {None, "", "all", "borehole", "soillayers", "every layer"}
    if object_name is None or object_name.strip().lower() in generic_names:
        messages = []
        for i, layer in enumerate(g.Soillayers):
            messages.append(_assign_to_layer(layer, f"Soillayer_{i + 1}"))
        return " | ".join(messages) if messages else f"No soil layers found to assign '{material_name}'."

    # ── Try numeric pattern: 'Soillayer_1', 'SoilLayer 2', 'layer1', etc. ──
    match = re.search(r"(\d+)", object_name.strip())
    if match:
        layer_index = int(match.group(1)) - 1
        if 0 <= layer_index < len(g.Soillayers):
            return _assign_to_layer(g.Soillayers[layer_index], f"Soillayer_{layer_index + 1}")

    # ── Try to find by name in the Plaxis object tree ────────────────────────
    try:
        obj = connection_manager.find_object_by_name(object_name)
        # Check if this is a soil layer — try .Soil.Material path first
        try:
            obj_name = connection_manager._safe_attr(obj, "Name") or object_name
            connection_manager.call_command(
                f"set {obj_name}.Soil.Material {mat_obj_name}", server="input"
            )
            return f"Assigned '{material_name}' to '{obj_name}'."
        except Exception:
            pass
        if mat is not None:
            g.setmaterial(obj, mat)
        return f"Assigned '{material_name}' to '{object_name}'."
    except ValueError:
        pass

    # ── Last resort: assign to all soil layers ───────────────────────────────
    logger.warning(f"Object '{object_name}' not found; assigning '{material_name}' to all soil layers.")
    messages = []
    for i, layer in enumerate(g.Soillayers):
        messages.append(_assign_to_layer(layer, f"Soillayer_{i + 1}"))
    return " | ".join(messages) if messages else f"Could not assign '{material_name}': no layers found."
