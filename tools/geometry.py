import logging
from plaxis_connection import connection_manager

logger = logging.getLogger(__name__)


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


def _goto_structures_mode(g):
    try:
        g.gotostructures()
        return
    except Exception as e:
        logger.warning(f"Wrapper gotostructures() unavailable, falling back to native command: {e}")
    try:
        connection_manager.call_command("gotostructures", server="input")
    except Exception as e:
        logger.warning(f"Native command gotostructures is unavailable in this PLAXIS build: {e}")


def _create_borehole_object(g, x: float, y: float):
    """
    Create a borehole using the Python wrapper when available, otherwise
    fall back to the native PLAXIS command line syntax.
    """
    _goto_soil_mode(g)

    try:
        return g.borehole(x, y, 0.0)
    except Exception as e_xyz:
        logger.warning(f"Wrapper borehole(x, y, z) unavailable, trying 2D-style signature: {e_xyz}")

    try:
        return g.borehole(x, y)
    except Exception as e_xy:
        logger.warning(f"Wrapper borehole(x, y) unavailable, trying command fallback: {e_xy}")

    try:
        connection_manager.call_command(f"borehole {x} {y} 0", server="input")
    except Exception as e_cmd_xyz:
        logger.warning(f"Native command 'borehole {x} {y} 0' failed, trying 2-argument form: {e_cmd_xyz}")
        try:
            connection_manager.call_command(f"borehole {x} {y}", server="input")
        except Exception as e_cmd_xy:
            logger.warning(f"Native command 'borehole {x} {y}' failed, trying single-coordinate form: {e_cmd_xy}")
            connection_manager.call_command(f"borehole {x}", server="input")

    # After a native command call, re-read the latest borehole from the model.
    return g.Boreholes[-1]


def _add_soil_layer(g, thickness_hint: float = 0.0):
    _goto_soil_mode(g)
    try:
        return g.soillayer(thickness_hint)
    except Exception as e:
        logger.warning(f"Wrapper soillayer() unavailable, falling back to native command: {e}")
        return connection_manager.call_command(f"soillayer {thickness_hint}", server="input")

def create_borehole(x: float, y: float, layers: list):
    """
    Create a borehole with soil layer definitions.

    Args:
        x (float): x-coordinate.
        y (float): y-coordinate.
        layers (list): List of dicts, each with 'top' and 'bottom' depth values,
                       and optional 'material' name.
                       Example: [{"top": 0, "bottom": -5}, {"top": -5, "bottom": -15}]
    """
    s, g = connection_manager.get_input()
    bh = _create_borehole_object(g, x, y)

    # Soil layers in Plaxis 3D are GLOBAL, not per-borehole.
    # The borehole defines the depth/position of each global layer at that (x,y).
    # First, ensure enough global soil layers exist:
    existing_layers = len(g.Soillayers)
    for i in range(existing_layers, len(layers)):
        _add_soil_layer(g, 0)  # Add a new global soil layer with 0 thickness (will be set below)

    # Set the top/bottom for each layer at this borehole
    for i, layer_def in enumerate(layers):
        try:
            soil_layer = g.Soillayers[i]
            # Access the borehole-specific zone for this layer
            for zone in soil_layer.Zones:
                try:
                    zone_borehole = zone.Borehole.value if hasattr(zone.Borehole, "value") else zone.Borehole
                    if zone_borehole == bh or len(soil_layer.Zones) == 1:
                        if hasattr(zone.Top, "set"):
                            zone.Top.set(layer_def.get("top", 0))
                        else:
                            zone.Top = layer_def.get("top", 0)
                        if hasattr(zone.Bottom, "set"):
                            zone.Bottom.set(layer_def.get("bottom", -5))
                        else:
                            zone.Bottom = layer_def.get("bottom", -5)
                        break
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Could not set layer {i} properties: {e}")

    return f"Created borehole at ({x}, {y}) with {len(layers)} layers."

def create_surface(points: list):
    """
    Create a 3D surface from a list of coordinate values.

    Args:
        points (list): Flat list of coordinates [x1,y1,z1, x2,y2,z2, ...] or
                       nested list [[x1,y1,z1], [x2,y2,z2], ...].
    """
    s, g = connection_manager.get_input()
    _goto_structures_mode(g)

    # Flatten nested list if needed: [[0,0,0],[10,0,0]] -> [0,0,0,10,0,0]
    if points and isinstance(points[0], (list, tuple)):
        flat = []
        for p in points:
            flat.extend(p)
        points = flat

    try:
        surface = g.surface(*points)
    except Exception as e:
        logger.warning(f"Wrapper surface() unavailable, falling back to native command: {e}")
        connection_manager.call_command("surface " + " ".join(str(p) for p in points), server="input")
        surface = g.Surfaces[-1]
    return f"Created surface with {len(points) // 3} points: {surface.Name.value}"

def create_volume(points: list, **kwargs):
    """
    Create a soil volume boundary surface.

    In Plaxis 3D, volumes are bounded by surfaces.  This call creates the
    bounding surface; Plaxis generates the volume automatically when surfaces
    enclose a region.

    Args:
        points (list): Flat list [x1,y1,z1, x2,y2,z2, ...] or nested
                       [[x1,y1,z1], [x2,y2,z2], ...].
        **kwargs: Absorbed silently (guards against LLM hallucinating extra
                  parameters such as 'object_name').
    """
    if kwargs:
        logger.warning(f"create_volume received unexpected kwargs (ignored): {list(kwargs.keys())}")

    s, g = connection_manager.get_input()
    _goto_structures_mode(g)

    if points and isinstance(points[0], (list, tuple)):
        flat = []
        for p in points:
            flat.extend(p)
        points = flat

    try:
        surface = g.surface(*points)
    except Exception as e:
        logger.warning(f"Wrapper surface() unavailable, falling back to native command: {e}")
        connection_manager.call_command("surface " + " ".join(str(p) for p in points), server="input")
        surface = g.Surfaces[-1]
    return f"Created volume boundary surface from {len(points) // 3} points: {surface.Name.value}"

def extrude(object_name: str, direction: list, length: float):
    """
    Extrude a 2D object to 3D.

    Args:
        object_name (str): Name of the Plaxis object to extrude (e.g., 'Surface_1').
        direction (list): Unit direction vector [x, y, z].
        length (float): Length of extrusion.
    """
    s, g = connection_manager.get_input()
    obj = connection_manager.find_object_by_name(object_name)

    # Plaxis extrude() takes the full vector (direction * length), not separate args
    dx = direction[0] * length
    dy = direction[1] * length
    dz = direction[2] * length
    extruded = g.extrude(obj, dx, dy, dz)
    return f"Extruded {object_name} by {length} in direction {direction}."

def find_object_by_coordinates(x: float, y: float, z: float, collection: str = "Volumes"):
    """
    Find a Plaxis object by its physical coordinates using the BoundingBox property.

    Args:
        x (float): Target X coordinate.
        y (float): Target Y coordinate.
        z (float): Target Z coordinate.
        collection (str): The Plaxis collection to search (e.g., 'Volumes', 'Surfaces', 'Points').
    """
    obj = connection_manager.find_object_by_coordinates(x, y, z, collection)
    obj_name = connection_manager._safe_attr(obj, "Name") or "Unknown"
    return f"Found object at ({x}, {y}, {z}) in {collection}: {obj_name}"
