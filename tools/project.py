import logging
from plaxis_connection import connection_manager

logger = logging.getLogger(__name__)

def new_project():
    """
    Create a new blank Plaxis 3D project via remote scripting.

    In Plaxis 3D Remote Scripting the 'new project' action is issued on the
    global object (g_i), not the server wrapper (s_i).  We try the documented
    approach first and fall back gracefully.
    """
    s, g = connection_manager.get_input()

    # Primary: command on the global scripting object
    try:
        g.new()
        logger.info("New project created via g.new()")
        return "Created new Plaxis 3D project."
    except Exception as e1:
        logger.warning(f"g.new() failed ({e1}), trying s.new()...")

    # Fallback: command on the server wrapper
    try:
        s.new()
        logger.info("New project created via s.new()")
        return "Created new Plaxis 3D project."
    except Exception as e2:
        msg = (
            f"Could not create new project automatically "
            f"(g.new: {e1} / s.new: {e2}). "
            "Please create or open a project manually in Plaxis 3D first, "
            "then re-issue your command."
        )
        logger.error(msg)
        raise RuntimeError(msg)

def open_project(path: str):
    """
    Open an existing .p3d file.
    """
    s, g = connection_manager.get_input()
    s.open(path)
    return f"Opened project at {path}."

def save_project(path: str):
    """
    Save the current project.
    """
    s, g = connection_manager.get_input()
    s.save(path)
    return f"Saved project to {path}."

def close_project():
    """
    Close project without saving.
    """
    s, g = connection_manager.get_input()
    s.close()
    return "Closed project."
