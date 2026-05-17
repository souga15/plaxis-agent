import logging
from plaxis_connection import connection_manager

logger = logging.getLogger(__name__)

def get_displacements(phase_name: str, point: list = None):
    """
    Get displacement components (Ux, Uy, Uz) in a phase.

    When *point* is provided as [x, y, z], returns displacements at that
    specific location using ``getsingleresult``.  When *point* is ``None``,
    returns the max/min envelope over the entire model.

    Args:
        phase_name (str): Name of the calculation phase.
        point (list, optional): [x, y, z] coordinates of the query point.
    """
    s_o, g_o = connection_manager.get_output()
    phase = connection_manager.find_object_by_name(phase_name, server="output")

    try:
        if point and len(point) >= 3:
            # Point-specific query
            x, y, z = float(point[0]), float(point[1]), float(point[2])
            ux = g_o.getsingleresult(phase, g_o.ResultTypes.Soil.Ux, (x, y, z))
            uy = g_o.getsingleresult(phase, g_o.ResultTypes.Soil.Uy, (x, y, z))
            uz = g_o.getsingleresult(phase, g_o.ResultTypes.Soil.Uz, (x, y, z))
            return {
                "phase": phase_name,
                "point": point,
                "Ux": ux,
                "Uy": uy,
                "Uz": uz,
            }
        else:
            # Full-model envelope
            ux = g_o.getresults(phase, g_o.ResultTypes.Soil.Ux, "node")
            uy = g_o.getresults(phase, g_o.ResultTypes.Soil.Uy, "node")
            uz = g_o.getresults(phase, g_o.ResultTypes.Soil.Uz, "node")
            return {
                "phase": phase_name,
                "Ux_max": max(ux) if ux else "N/A",
                "Uy_max": max(uy) if uy else "N/A",
                "Uz_max": min(uz) if uz else "N/A",  # min for settlement (negative)
                "note": "No point specified — showing max/min envelope values.",
            }
    except Exception as e:
        logger.error(f"Error getting displacements: {e}")
        return {"error": str(e), "phase": phase_name, "point": point}

def get_stresses(phase_name: str, point: list = None):
    """
    Get effective stress state in a phase.

    When *point* is provided as [x, y, z], returns stresses at that
    specific location.  Otherwise returns the min envelope.

    Args:
        phase_name (str): Name of the calculation phase.
        point (list, optional): [x, y, z] coordinates.
    """
    s_o, g_o = connection_manager.get_output()
    phase = connection_manager.find_object_by_name(phase_name, server="output")

    try:
        if point and len(point) >= 3:
            x, y, z = float(point[0]), float(point[1]), float(point[2])
            sig_xx = g_o.getsingleresult(phase, g_o.ResultTypes.Soil.SigxxE, (x, y, z))
            sig_yy = g_o.getsingleresult(phase, g_o.ResultTypes.Soil.SigyyE, (x, y, z))
            sig_zz = g_o.getsingleresult(phase, g_o.ResultTypes.Soil.SigzzE, (x, y, z))
            return {
                "phase": phase_name,
                "point": point,
                "sigma_xx": sig_xx,
                "sigma_yy": sig_yy,
                "sigma_zz": sig_zz,
            }
        else:
            sig_xx = g_o.getresults(phase, g_o.ResultTypes.Soil.SigxxE, "node")
            sig_yy = g_o.getresults(phase, g_o.ResultTypes.Soil.SigyyE, "node")
            sig_zz = g_o.getresults(phase, g_o.ResultTypes.Soil.SigzzE, "node")
            return {
                "phase": phase_name,
                "sigma_xx_min": min(sig_xx) if sig_xx else "N/A",
                "sigma_yy_min": min(sig_yy) if sig_yy else "N/A",
                "sigma_zz_min": min(sig_zz) if sig_zz else "N/A",
                "note": "No point specified — showing min envelope values.",
            }
    except Exception as e:
        logger.error(f"Error getting stresses: {e}")
        return {"error": str(e), "phase": phase_name}

def get_structural_forces(phase_name: str, structure_name: str):
    """
    Get axial force (N), bending moment (M), and shear force (V)
    for a specific structural element (e.g., a plate).

    Args:
        phase_name (str): Phase name.
        structure_name (str): Name of the structural element (e.g., 'Plate_1').
    """
    s_o, g_o = connection_manager.get_output()
    phase = connection_manager.find_object_by_name(phase_name, server="output")
    structure = connection_manager.find_object_by_name(structure_name, server="output")

    try:
        N = g_o.getresults(structure, phase, g_o.ResultTypes.Plate.Nx2D, "node")
        M = g_o.getresults(structure, phase, g_o.ResultTypes.Plate.M2D, "node")
        Q = g_o.getresults(structure, phase, g_o.ResultTypes.Plate.Q2D, "node")

        return {
            "phase": phase_name,
            "structure": structure_name,
            "N_max": max(N) if N else "N/A",
            "N_min": min(N) if N else "N/A",
            "M_max": max(M) if M else "N/A",
            "M_min": min(M) if M else "N/A",
            "Q_max": max(Q) if Q else "N/A",
            "Q_min": min(Q) if Q else "N/A",
        }
    except Exception as e:
        logger.error(f"Error getting structural forces: {e}")
        return {"error": str(e)}

def get_safety_factor(phase_name: str):
    """
    Get the safety factor (Sum-Msf) from a Safety/phi-c reduction phase.

    Args:
        phase_name (str): Name of the safety phase.
    """
    s_o, g_o = connection_manager.get_output()
    phase = connection_manager.find_object_by_name(phase_name, server="output")

    try:
        msf = g_o.getresults(phase, g_o.ResultTypes.Soil.SumMsf, "node")

        # The safety factor is the last converged Sum-Msf value
        safety_factor = msf[-1] if msf else "N/A"
        return {
            "phase": phase_name,
            "safety_factor": safety_factor,
        }
    except Exception as e:
        logger.error(f"Error getting safety factor: {e}")
        return {"error": str(e), "phase": phase_name}

def export_results_to_excel(phase_name: str, output_path: str):
    """
    Export phase results to an Excel file using openpyxl.

    Args:
        phase_name (str): Phase to export.
        output_path (str): File path for the output .xlsx file.
    """
    try:
        import openpyxl

        s_o, g_o = connection_manager.get_output()
        phase = connection_manager.find_object_by_name(phase_name, server="output")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Results - {phase_name}"

        # Write displacement results
        ws.append(["Result Type", "Max Value", "Min Value"])

        for result_name, result_type in [
            ("Ux", g_o.ResultTypes.Soil.Ux),
            ("Uy", g_o.ResultTypes.Soil.Uy),
            ("Uz", g_o.ResultTypes.Soil.Uz),
        ]:
            try:
                values = g_o.getresults(phase, result_type, "node")
                ws.append([result_name, max(values), min(values)])
            except Exception:
                ws.append([result_name, "Error", "Error"])

        wb.save(output_path)
        return f"Exported results of '{phase_name}' to {output_path}"

    except ImportError:
        return "Error: openpyxl is not installed. Run: pip install openpyxl"
    except Exception as e:
        logger.error(f"Error exporting results: {e}")
        return f"Error exporting: {str(e)}"
