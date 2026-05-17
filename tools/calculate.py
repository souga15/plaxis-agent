import logging
from plaxis_connection import connection_manager

logger = logging.getLogger(__name__)

def run_calculation():
    """
    Execute all pending calculation phases.
    Switches to the Staged Construction mode first, then calculates.
    """
    s, g = connection_manager.get_input()
    try:
        g.gotostages()
    except Exception as e:
        logger.warning(f"Wrapper gotostages() unavailable, falling back to native command: {e}")
        try:
            connection_manager.call_command("gotostages", server="input")
        except Exception as e2:
            logger.warning(f"Native command gotostages is unavailable in this PLAXIS build: {e2}")

    try:
        g.calculate()
    except Exception as e:
        logger.warning(f"Wrapper calculate() unavailable, falling back to native command: {e}")
        connection_manager.call_command("calculate", server="input")
    return "Started calculation for all pending phases."

def get_calculation_status():
    """
    Check calculation progress and convergence for each phase.
    """
    s, g = connection_manager.get_input()
    
    status_list = []
    try:
        for phase in g.Phases:
            try:
                phase_status = {
                    "name": phase.Identification.value if hasattr(phase.Identification, 'value') else str(phase),
                    "status": str(phase.LogInfo.value) if hasattr(phase, 'LogInfo') else "unknown",
                }
                status_list.append(phase_status)
            except Exception:
                status_list.append({"name": str(phase), "status": "unknown"})
    except Exception as e:
        logger.warning(f"Could not get calculation status: {e}")
        return {"status": "error", "message": str(e)}
    
    return {"phases": status_list}

def get_log():
    """
    Return the calculation log messages from the last calculation run.
    """
    s, g = connection_manager.get_input()
    
    try:
        log_entries = []
        for phase in g.Phases:
            try:
                log_info = phase.LogInfo.value if hasattr(phase, 'LogInfo') else ""
                if log_info:
                    phase_name = phase.Identification.value if hasattr(phase.Identification, 'value') else str(phase)
                    log_entries.append(f"[{phase_name}] {log_info}")
            except Exception:
                pass
        
        return {"log": "\n".join(log_entries) if log_entries else "No log entries available."}
    except Exception as e:
        return {"log": f"Error reading log: {str(e)}"}
