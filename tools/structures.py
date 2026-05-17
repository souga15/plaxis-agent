import logging
from plaxis_connection import connection_manager

logger = logging.getLogger(__name__)

def create_plate(points: list):
    """
    Create a plate structure (e.g., retaining wall, slab).

    Args:
        points (list): Flat list [x1,y1,z1, x2,y2,z2,...] or nested [[x1,y1,z1],...]
    """
    s, g = connection_manager.get_input()

    if points and isinstance(points[0], (list, tuple)):
        flat = []
        for p in points:
            flat.extend(p)
        points = flat

    plate = g.plate(*points)
    return f"Created plate with {len(points) // 3} corner points."

def create_anchor(point1: list, point2: list):
    """
    Create a node-to-node anchor between two points.

    Args:
        point1 (list): Start point [x, y, z].
        point2 (list): End point [x, y, z].
    """
    s, g = connection_manager.get_input()
    anchor = g.nodetonode(*point1, *point2)
    return f"Created node-to-node anchor from {point1} to {point2}."

def create_pile(point: list, depth: float):
    """
    Create an embedded beam (pile).

    Args:
        point (list): [x, y] position of the pile head.
        depth (float): Depth of the pile from surface.
    """
    s, g = connection_manager.get_input()
    # Create an embedded beam row at the given location
    pile = g.embeddedbeam(point[0], point[1], 0, point[0], point[1], -depth)
    return f"Created embedded beam (pile) at ({point[0]}, {point[1]}) with depth {depth}m."

def create_interface(object_name: str):
    """
    Create positive and negative soil-structure interfaces around an object.

    Args:
        object_name (str): Name of the structural object (e.g., 'Plate_1').
    """
    s, g = connection_manager.get_input()
    obj = connection_manager.find_object_by_name(object_name)
    g.posinterface(obj)
    g.neginterface(obj)
    return f"Created positive and negative interfaces for {object_name}."

def create_load(load_type: str, points: list, value: list):
    """
    Create a surface or line load.

    Args:
        load_type (str): 'surface' or 'line'.
        points (list): Coordinates defining the load geometry.
        value (list): Load values [qx, qy, qz] in kN/m² or kN/m.
    """
    s, g = connection_manager.get_input()

    if points and isinstance(points[0], (list, tuple)):
        flat = []
        for p in points:
            flat.extend(p)
        points = flat

    if load_type.lower() == "surface":
        load = g.surfload(*points)
    else:
        load = g.lineload(*points)

    # Set load values
    if value and len(value) >= 3:
        load.qx_start = value[0]
        load.qy_start = value[1]
        load.qz_start = value[2]

    return f"Created {load_type} load with values {value}."
