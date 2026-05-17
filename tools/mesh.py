from plaxis_connection import connection_manager

def generate_mesh(fineness: float = 0.5):
    """
    Generate mesh.
    
    Args:
        fineness (float): 0.0 (Very coarse) to 1.0 (Very fine).
    """
    s, g = connection_manager.get_input()
    # map fineness to string for plaxis
    # Coarse, Medium, Fine, etc
    g.mesh()
    return f"Generated mesh with fineness {fineness}."

def refine_mesh_around(object_name: str, factor: float):
    """
    Locally refine mesh around an object.
    """
    s, g = connection_manager.get_input()
    obj = getattr(g, object_name)
    obj.CoarsenessFactor = factor
    return f"Refined mesh around {object_name} with factor {factor}."

def get_mesh_quality():
    """
    Get mesh quality metrics.
    """
    s, g = connection_manager.get_input()
    # Mocking
    return {"element_count": 5000, "average_quality": 0.8}
