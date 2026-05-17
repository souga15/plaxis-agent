from plaxis_connection import connection_manager

def new_project():
    """
    Create a new blank project.
    """
    s, g = connection_manager.get_input()
    s.new()
    return "Created new Plaxis project."

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
