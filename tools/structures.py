import logging
from plaxis_connection import connection_manager

logger = logging.getLogger(__name__)

def _goto_structures_mode(g):
    try:
        g.gotostructures()
        return
    except Exception as e:
        logger.warning(f"Wrapper gotostructures() unavailable: {e}")
    try:
        connection_manager.call_command("gotostructures", server="input")
    except Exception as e:
        logger.warning(f"Native command gotostructures unavailable: {e}")

def create_plate(points: list):
    """
    Create a plate structure (e.g., retaining wall, slab).

    Args:
        points (list): Flat list [x1,y1,z1, x2,y2,z2,...] or nested [[x1,y1,z1],...]
    """
    s, g = connection_manager.get_input()
    _goto_structures_mode(g)

    if points and isinstance(points[0], (list, tuple)):
        flat = []
        for p in points:
            flat.extend(p)
        points = flat

    try:
        plate = g.plate(*points)
    except Exception as e:
        logger.warning(f"Wrapper plate() unavailable, falling back to native command: {e}")
        points_str = " ".join(str(p) for p in points)
        connection_manager.call_command(f"plate {points_str}", server="input")

    return f"Created plate with {len(points) // 3} corner points."

def create_anchor(point1: list, point2: list):
    """
    Create a node-to-node anchor between two points.

    Args:
        point1 (list): Start point [x, y, z].
        point2 (list): End point [x, y, z].
    """
    s, g = connection_manager.get_input()
    _goto_structures_mode(g)
    
    try:
        anchor = g.nodetonode(*point1, *point2)
    except Exception as e:
        logger.warning(f"Wrapper nodetonode() unavailable, falling back to native command: {e}")
        p1_str = " ".join(str(p) for p in point1)
        p2_str = " ".join(str(p) for p in point2)
        connection_manager.call_command(f"nodetonode {p1_str} {p2_str}", server="input")
        
    return f"Created node-to-node anchor from {point1} to {point2}."

def create_pile(point: list, depth: float):
    """
    Create an embedded beam (pile) or embedded beam row (2D).

    Args:
        point (list): [x, y] position of the pile head.
        depth (float): Depth of the pile from surface.
    """
    s, g = connection_manager.get_input()
    _goto_structures_mode(g)
    
    # Check if we are in a 2D environment (2 coordinates) vs 3D (3 coordinates)
    # Usually the prompt tells LLM to pass [x, y], so we handle both
    if len(point) == 2:
        # 2D case: embeddedbeamrow from (x, y) to (x, y-depth)
        try:
            pile = g.embeddedbeamrow(point[0], point[1], point[0], point[1] - depth)
        except Exception as e:
            logger.warning(f"Wrapper embeddedbeamrow() unavailable, falling back: {e}")
            connection_manager.call_command(f"embeddedbeamrow {point[0]} {point[1]} {point[0]} {point[1] - depth}", server="input")
    else:
        # 3D case: embeddedbeam from (x, y, z) to (x, y, z-depth)
        try:
            pile = g.embeddedbeam(point[0], point[1], point[2] if len(point)>2 else 0, point[0], point[1], (point[2] if len(point)>2 else 0) - depth)
        except Exception as e:
            logger.warning(f"Wrapper embeddedbeam() unavailable, falling back: {e}")
            z = point[2] if len(point) > 2 else 0
            connection_manager.call_command(f"embeddedbeam {point[0]} {point[1]} {z} {point[0]} {point[1]} {z - depth}", server="input")
        
    return f"Created embedded beam (pile) at {point} with depth {depth}m."

def create_interface(object_name: str):
    """
    Create positive and negative soil-structure interfaces around an object.

    Args:
        object_name (str): Name of the structural object (e.g., 'Plate_1').
    """
    s, g = connection_manager.get_input()
    _goto_structures_mode(g)
    
    obj = connection_manager.find_object_by_name(object_name)
    try:
        g.posinterface(obj)
        g.neginterface(obj)
    except Exception as e:
        logger.warning(f"Wrapper interface unavailable, falling back to native command: {e}")
        # Need to safely get object name
        obj_name = getattr(obj, "Name", None)
        if obj_name is not None:
            obj_name = obj_name.value if hasattr(obj_name, 'value') else str(obj_name)
        else:
            obj_name = object_name
            
        connection_manager.call_command(f"posinterface {obj_name}", server="input")
        connection_manager.call_command(f"neginterface {obj_name}", server="input")
        
    return f"Created positive and negative interfaces for {object_name}."

def create_load(load_type: str, points: list, value: list):
    """
    Create a surface, line, or point load.

    Args:
        load_type (str): 'surface', 'line', or 'point'.
        points (list): Coordinates defining the load geometry.
        value (list): Load values [qx, qy, qz] in kN/m² or kN/m.
    """
    s, g = connection_manager.get_input()
    _goto_structures_mode(g)

    if points and isinstance(points[0], (list, tuple)):
        flat = []
        for p in points:
            flat.extend(p)
        points = flat

    lt = load_type.lower().strip()
    try:
        if lt in {"surface", "surfload"}:
            load = g.surfload(*points)
            load_collection = getattr(g, "SurfaceLoads", [])
        elif lt in {"point", "pointload"}:
            load = g.pointload(*points)
            load_collection = getattr(g, "PointLoads", [])
        else:
            load = g.lineload(*points)
            load_collection = getattr(g, "LineLoads", [])
    except Exception as e:
        logger.warning(f"Wrapper load unavailable, falling back to native command: {e}")
        points_str = " ".join(str(p) for p in points)
        if lt in {"surface", "surfload"}:
            cmd_type = "surfload"
            col_name = "SurfaceLoads"
        elif lt in {"point", "pointload"}:
            cmd_type = "pointload"
            col_name = "PointLoads"
        else:
            cmd_type = "lineload"
            col_name = "LineLoads"
        connection_manager.call_command(f"{cmd_type} {points_str}", server="input")
        
        # We need to get the last created load to assign values
        try:
            load_collection = getattr(g, col_name, [])
            load = load_collection[-1] if len(load_collection) > 0 else None
        except Exception:
            load = None

    # Set load values
    if load is not None and value and len(value) >= 3:
        try:
            load.qx_start = value[0]
            load.qy_start = value[1]
            load.qz_start = value[2]
        except Exception as e:
            logger.warning(f"Direct load value assignment failed, falling back to native: {e}")
            load_name = getattr(load, "Name", None)
            if load_name is not None:
                load_name = load_name.value if hasattr(load_name, 'value') else str(load_name)
                connection_manager.call_command(f"set {load_name}.qx_start {value[0]}", server="input")
                connection_manager.call_command(f"set {load_name}.qy_start {value[1]}", server="input")
                connection_manager.call_command(f"set {load_name}.qz_start {value[2]}", server="input")

    return f"Created {load_type} load with values {value}."
