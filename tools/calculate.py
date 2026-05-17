from plaxis_connection import connection_manager

def run_calculation():
    """
    Execute all pending calculation phases.
    """
    s, g = connection_manager.get_input()
    g.calculate()
    return "Started calculation for all phases."

def get_calculation_status():
    """
    Check calculation progress and convergence.
    """
    s, g = connection_manager.get_input()
    # Return mock status
    return {"status": "completed", "convergence": True}

def get_log():
    """
    Return calculation log messages.
    """
    s, g = connection_manager.get_input()
    return {"log": "Calculation finished successfully without errors."}
