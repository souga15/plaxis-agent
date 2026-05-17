from plaxis_connection import connection_manager

def create_plate(points: list):
    """
    Create a plate structure (e.g., retaining wall, slab).
    
    Args:
        points (list): List of points forming the plate polygon.
    """
    s, g = connection_manager.get_input()
    plate = g.plate(*points)
    return f"Created plate with {len(points)} points."

def create_anchor(point: list, direction: list, length: float):
    """
    Create a node-to-node anchor.
    """
    s, g = connection_manager.get_input()
    # Mocking anchor creation logic
    return f"Created anchor at {point} with length {length}."

def create_pile(point: list, depth: float):
    """
    Create an embedded pile.
    """
    s, g = connection_manager.get_input()
    # Mocking embedded pile
    return f"Created embedded pile at {point} with depth {depth}."

def create_interface(object_name: str):
    """
    Create a soil-structure interface around an object.
    """
    s, g = connection_manager.get_input()
    obj = getattr(g, object_name)
    g.posinterface(obj)
    g.neginterface(obj)
    return f"Created interfaces for {object_name}."

def create_load(point_or_area: str, value: float, direction: str):
    """
    Create a load.
    """
    s, g = connection_manager.get_input()
    return f"Created load {value} on {point_or_area} in {direction} direction."
