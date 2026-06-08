"""
Template: Shallow/Deep Foundation Bearing Capacity
Creates a foundation model with:
- Soil stratigraphy
- Foundation slab (plate element)
- Loading phases for bearing capacity analysis
"""
import logging
from plaxis_connection import connection_manager
from tools.geometry import create_borehole
from tools.materials import create_soil_material, create_plate_material
from tools.structures import create_plate
from tools.phases import add_phase
from tools.mesh import generate_mesh

logger = logging.getLogger(__name__)

def run_foundation_template(
    foundation_width: float = 3.0,
    foundation_length: float = 3.0,
    foundation_depth: float = 1.5,
    load: float = 500.0,
):
    """
    Create a foundation bearing capacity model.

    Args:
        foundation_width: Width of the footing (m).
        foundation_length: Length of the footing (m).
        foundation_depth: Embedment depth (m).
        load: Applied load in kN/m².
    """
    results = []
    s, g = connection_manager.get_input()

    try:
        s.new()
        results.append("Created new project")

        # Soil layers
        layers = [
            {"top": 0, "bottom": -2},       # Topsoil / Fill
            {"top": -2, "bottom": -10},      # Medium clay
            {"top": -10, "bottom": -25},     # Stiff clay / sand
        ]
        create_borehole(0, 0, layers)
        results.append("Created 3-layer stratigraphy")

        # Soil materials
        create_soil_material("Topsoil", "Mohr-Coulomb", {
            "gammaUnsat": 16.0, "gammaSat": 18.0,
            "Eref": 10000, "nu": 0.3,
            "cref": 2.0, "phi": 25.0,
        })
        create_soil_material("Medium Clay", "Mohr-Coulomb", {
            "gammaUnsat": 17.5, "gammaSat": 19.5,
            "Eref": 25000, "nu": 0.35,
            "cref": 15.0, "phi": 22.0,
        })
        create_soil_material("Stiff Clay", "Mohr-Coulomb", {
            "gammaUnsat": 19.0, "gammaSat": 21.0,
            "Eref": 50000, "nu": 0.3,
            "cref": 25.0, "phi": 28.0,
        })
        results.append("Created 3 soil materials")

        # Foundation plate
        g.gotostructures()
        half_w = foundation_width / 2
        half_l = foundation_length / 2
        z = -foundation_depth

        plate_points = [
            -half_w, -half_l, z,
            half_w, -half_l, z,
            half_w, half_l, z,
            -half_w, half_l, z,
        ]
        g.plate(*plate_points)
        results.append(f"Created foundation plate ({foundation_width}x{foundation_length}m at {foundation_depth}m depth)")

        # Foundation material
        create_plate_material("Concrete Foundation", {
            "d": 0.5,
            "E1": 30e6,
            "nu12": 0.15,
            "w": 12.0,
        })
        results.append("Created concrete foundation material")

        # Surface load on foundation
        g.surfload(*plate_points)
        results.append(f"Created surface load ({load} kN/m²)")

        # Mesh
        generate_mesh(0.6)
        results.append("Generated mesh")

        # Phases
        add_phase("Foundation Placement", "Plastic")
        add_phase("Loading", "Plastic")
        add_phase("Safety Analysis", "Safety")
        results.append("Created 3 phases (placement, loading, safety)")

        return {
            "status": "success",
            "message": "Foundation template created successfully.",
            "details": results,
            "parameters": {
                "foundation_width": foundation_width,
                "foundation_length": foundation_length,
                "foundation_depth": foundation_depth,
                "applied_load": load,
            }
        }
    except Exception as e:
        logger.error(f"Foundation template failed: {e}")
        return {"status": "error", "message": str(e), "completed_steps": results}
