import logging
from plaxis_connection import connection_manager

logger = logging.getLogger(__name__)

# Plaxis mesh fineness mapping (Element Distribution)
FINENESS_MAP = {
    "very coarse": 5,
    "coarse": 4,
    "medium": 3,
    "fine": 2,
    "very fine": 1,
}

def _map_fineness(fineness: float) -> str:
    """Map a 0.0–1.0 float to a Plaxis fineness category string."""
    if fineness <= 0.1:
        return "very coarse"
    elif fineness <= 0.3:
        return "coarse"
    elif fineness <= 0.6:
        return "medium"
    elif fineness <= 0.8:
        return "fine"
    else:
        return "very fine"

def generate_mesh(fineness: float = 0.5):
    """
    Generate mesh with the specified fineness.

    Args:
        fineness (float): 0.0 (Very coarse) to 1.0 (Very fine).
    """
    s, g = connection_manager.get_input()

    category = _map_fineness(fineness)
    fineness_value = FINENESS_MAP[category]

    # Set the mesh fineness before generating
    try:
        g.gotomesh()
    except Exception as e:
        logger.warning(f"Wrapper gotomesh() unavailable, falling back to native command: {e}")
        try:
            connection_manager.call_command("gotomesh", server="input")
        except Exception as e2:
            logger.warning(f"Native command gotomesh is unavailable in this PLAXIS build: {e2}")

    try:
        g.mesh(fineness_value)
    except Exception as e:
        logger.warning(f"Wrapper mesh() unavailable, falling back to native command: {e}")
        connection_manager.call_command(f"mesh {fineness_value}", server="input")
    
    logger.info(f"Generated mesh with fineness '{category}' (value={fineness_value})")
    return f"Generated mesh with fineness '{category}' (input={fineness})."

def refine_mesh_around(object_name: str, factor: float):
    """
    Locally refine mesh around an object by setting its coarseness factor.

    Args:
        object_name (str): Name of the Plaxis object.
        factor (float): Coarseness factor (< 1.0 = finer, > 1.0 = coarser). Typical: 0.25
    """
    s, g = connection_manager.get_input()
    obj = connection_manager.find_object_by_name(object_name)
    obj.CoarsenessFactor = factor
    return f"Set mesh coarseness factor to {factor} for {object_name}."

def get_mesh_quality():
    """
    Get mesh quality metrics (element count and quality statistics).
    """
    s, g = connection_manager.get_input()
    
    try:
        try:
            g.gotomesh()
        except Exception:
            try:
                connection_manager.call_command("gotomesh", server="input")
            except Exception:
                pass
        info = {
            "element_count": g.Mesh.NumberOfElements.value if hasattr(g.Mesh, 'NumberOfElements') else "N/A",
            "node_count": g.Mesh.NumberOfNodes.value if hasattr(g.Mesh, 'NumberOfNodes') else "N/A",
        }
        return info
    except Exception as e:
        logger.warning(f"Could not retrieve mesh quality: {e}")
        return {"element_count": "N/A", "node_count": "N/A", "error": str(e)}
