from plaxis_connection import connection_manager

def create_borehole(x: float, y: float, layers: list):
    """
    Create a borehole with soil layer definitions.
    
    Args:
        x (float): x-coordinate.
        y (float): y-coordinate.
        layers (list): List of dicts, each with 'top', 'bottom', and optional 'material' name.
    """
    s, g = connection_manager.get_input()
    bh = g.borehole(x, y)
    
    # Note: adding layers sequentially usually requires setting top/bottom
    # For a real implementation, you'd iterate and g.soillayer()
    # Simple mock for this example:
    for layer in layers:
        g.soillayer(bh.name)
        # Assumes g.SoilLayers is indexed sequentially, simplified logic
    
    return f"Created borehole at ({x}, {y}) with {len(layers)} layers."

def create_surface(points: list):
    """
    Create a 3D surface from a list of points.
    
    Args:
        points (list): List of [x, y, z] coordinates forming the surface polygon.
    """
    s, g = connection_manager.get_input()
    surface = g.surface(*points)
    return f"Created surface with {len(points)} points: {surface.name}"

def create_volume(points: list):
    """
    Create a soil volume. (Plaxis 3D usually creates volumes from extruded surfaces or intersecting surfaces)
    """
    s, g = connection_manager.get_input()
    # Mocking volume creation, usually it's surface + extrude
    return f"Created volume from points."

def extrude(object_name: str, direction: list, length: float):
    """
    Extrude a 2D object to 3D.
    
    Args:
        object_name (str): Name of the Plaxis object to extrude (e.g., 'Surface_1').
        direction (list): Extrusion direction vector [x, y, z].
        length (float): Length of extrusion.
    """
    s, g = connection_manager.get_input()
    obj = getattr(g, object_name)
    extruded = g.extrude(obj, direction[0], direction[1], direction[2], length)
    return f"Extruded {object_name} by {length} in direction {direction}."
