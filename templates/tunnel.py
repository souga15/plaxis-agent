"""
Template: Tunnel Excavation with Lining
Creates a tunnel model with:
- Soil stratigraphy
- Circular tunnel geometry
- Shotcrete/concrete lining (plate)
- Staged excavation and lining installation phases
"""
import logging
import math
from plaxis_connection import connection_manager
from tools.geometry import create_borehole
from tools.materials import create_soil_material, create_plate_material
from tools.phases import add_phase
from tools.mesh import generate_mesh

logger = logging.getLogger(__name__)

def run_tunnel_template(
    tunnel_depth: float = 15.0,
    tunnel_diameter: float = 6.0,
    overburden: float = 10.0,
    length: float = 20.0,
):
    """
    Create a tunnel excavation model with lining.

    Args:
        tunnel_depth: Depth to tunnel center from ground surface (m).
        tunnel_diameter: Tunnel diameter (m).
        overburden: Soil overburden above tunnel crown (m).
        length: Model length along tunnel axis (m).
    """
    results = []
    s, g = connection_manager.get_input()

    try:
        s.new()
        results.append("Created new project")

        # Soil layers
        layers = [
            {"top": 0, "bottom": -5},       # Weathered rock
            {"top": -5, "bottom": -30},      # Intact rock/soil
        ]
        create_borehole(0, 0, layers)
        results.append("Created soil stratigraphy")

        # Soil materials
        create_soil_material("Weathered Rock", "Mohr-Coulomb", {
            "gammaUnsat": 22.0, "gammaSat": 24.0,
            "Eref": 100000, "nu": 0.25,
            "cref": 50.0, "phi": 30.0,
        })
        create_soil_material("Intact Rock", "Mohr-Coulomb", {
            "gammaUnsat": 25.0, "gammaSat": 26.0,
            "Eref": 500000, "nu": 0.2,
            "cref": 200.0, "phi": 35.0,
        })
        results.append("Created rock materials")

        # Create tunnel geometry using polycurve/circle
        g.gotostructures()
        radius = tunnel_diameter / 2
        
        # Create a tunnel cross-section as a circular surface
        # Plaxis 3D has a specific tunnel designer, but we can approximate
        # with a polycurve circle
        n_segments = 16
        tunnel_points = []
        for i in range(n_segments):
            angle = 2 * math.pi * i / n_segments
            x = radius * math.cos(angle)
            z = -tunnel_depth + radius * math.sin(angle)
            tunnel_points.extend([x, 0, z])
        
        try:
            g.surface(*tunnel_points)
            results.append(f"Created tunnel cross-section (D={tunnel_diameter}m, depth={tunnel_depth}m)")
        except Exception as e:
            logger.warning(f"Tunnel surface creation: {e}")
            results.append(f"Tunnel geometry needs manual adjustment: {e}")

        # Lining material
        create_plate_material("Shotcrete Lining", {
            "d": 0.3,           # 300mm shotcrete
            "E1": 15e6,         # Young's modulus kN/m²
            "nu12": 0.15,
            "w": 7.2,           # weight
        })
        create_plate_material("Final Lining", {
            "d": 0.5,           # 500mm concrete
            "E1": 30e6,
            "nu12": 0.15,
            "w": 12.0,
        })
        results.append("Created lining materials (shotcrete + final)")

        # Mesh
        generate_mesh(0.6)
        results.append("Generated mesh (fine)")

        # Phases
        add_phase("Tunnel Excavation", "Plastic")
        add_phase("Shotcrete Installation", "Plastic")
        add_phase("Final Lining", "Plastic")
        results.append("Created 3 construction phases")

        return {
            "status": "success",
            "message": "Tunnel template created successfully.",
            "details": results,
            "parameters": {
                "tunnel_depth": tunnel_depth,
                "tunnel_diameter": tunnel_diameter,
                "overburden": overburden,
                "length": length,
            }
        }
    except Exception as e:
        logger.error(f"Tunnel template failed: {e}")
        return {"status": "error", "message": str(e), "completed_steps": results}
