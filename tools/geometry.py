import logging
from plaxis_connection import connection_manager

logger = logging.getLogger(__name__)

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
    bh = g.borehole(x, y)

    # Soil layers in Plaxis 3D are GLOBAL, not per-borehole.
    # The borehole defines the depth/position of each global layer at that (x,y).
    # First, ensure enough global soil layers exist:
    existing_layers = len(g.Soillayers)
    for i in range(existing_layers, len(layers)):
        g.soillayer(0)  # Add a new global soil layer with 0 thickness (will be set below)

    # Set the top/bottom for each layer at this borehole
    for i, layer_def in enumerate(layers):
        try:
            soil_layer = g.Soillayers[i]
            # Access the borehole-specific zone for this layer
            for zone in soil_layer.Zones:
                try:
                    if zone.Borehole.value == bh:
                        zone.Top = layer_def.get("top", 0)
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

    # Flatten nested list if needed: [[0,0,0],[10,0,0]] -> [0,0,0,10,0,0]
    if points and isinstance(points[0], (list, tuple)):
        flat = []
        for p in points:
            flat.extend(p)
        points = flat

    surface = g.surface(*points)
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

    if points and isinstance(points[0], (list, tuple)):
        flat = []
        for p in points:
            flat.extend(p)
        points = flat

    surface = g.surface(*points)
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
