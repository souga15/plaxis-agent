"""
Template: Slope Stability with Phi/c Reduction
Creates a slope stability model with:
- Natural slope geometry
- Soil layers
- Safety analysis using strength reduction method
"""
import logging
from plaxis_connection import connection_manager
from tools.geometry import create_borehole
from tools.materials import create_soil_material
from tools.phases import add_phase
from tools.mesh import generate_mesh

logger = logging.getLogger(__name__)

def run_slope_stability_template(
    slope_height: float = 10.0,
    slope_angle_deg: float = 45.0,
    soil_cohesion: float = 10.0,
    soil_friction: float = 25.0,
):
    """
    Create a slope stability model with phi/c reduction safety analysis.

    Args:
        slope_height: Height of the slope (m).
        slope_angle_deg: Slope angle in degrees from horizontal.
        soil_cohesion: Cohesion of the slope material (kN/m²).
        soil_friction: Friction angle of the slope material (degrees).
    """
    import math
    results = []
    s, g = connection_manager.get_input()

    try:
        s.new()
        results.append("Created new project")

        # Soil stratigraphy
        total_depth = slope_height + 10  # Extra depth below slope toe
        layers = [
            {"top": 0, "bottom": -3},                  # Weathered layer
            {"top": -3, "bottom": -total_depth},        # Main soil
        ]
        create_borehole(0, 0, layers)
        results.append("Created soil stratigraphy")

        # Soil materials
        create_soil_material("Weathered Soil", "Mohr-Coulomb", {
            "gammaUnsat": 17.0, "gammaSat": 19.0,
            "Eref": 15000, "nu": 0.3,
            "cref": soil_cohesion * 0.5,  # weaker surface layer
            "phi": soil_friction - 5,
        })
        create_soil_material("Slope Soil", "Mohr-Coulomb", {
            "gammaUnsat": 18.0, "gammaSat": 20.0,
            "Eref": 30000, "nu": 0.3,
            "cref": soil_cohesion,
            "phi": soil_friction,
        })
        results.append(f"Created soil materials (c'={soil_cohesion} kPa, φ'={soil_friction}°)")

        # Create slope geometry
        g.gotostructures()
        slope_run = slope_height / math.tan(math.radians(slope_angle_deg))
        
        # Slope surface as a polyline/surface
        # Define the slope face
        model_width = 20  # half-width in y direction
        slope_points = [
            0, -model_width, 0,                         # Toe left
            0, model_width, 0,                           # Toe right
            slope_run, model_width, slope_height,        # Crest right
            slope_run, -model_width, slope_height,       # Crest left
        ]
        try:
            g.surface(*slope_points)
            results.append(f"Created slope face ({slope_height}m high, {slope_angle_deg}° angle)")
        except Exception as e:
            results.append(f"Slope geometry needs manual refinement: {e}")

        # Mesh (finer for safety analysis)
        generate_mesh(0.7)
        results.append("Generated fine mesh for safety analysis")

        # Phases
        add_phase("Gravity Loading", "Plastic")
        add_phase("Phi/c Reduction (Safety)", "Safety")
        results.append("Created 2 phases (gravity + safety/phi-c reduction)")

        return {
            "status": "success",
            "message": "Slope stability template created. Run calculation to get Factor of Safety.",
            "details": results,
            "parameters": {
                "slope_height": slope_height,
                "slope_angle": slope_angle_deg,
                "cohesion": soil_cohesion,
                "friction_angle": soil_friction,
            },
            "next_steps": [
                "Assign materials to soil layers",
                "Review mesh quality",
                "Run calculation",
                "Check Sum-Msf (Factor of Safety) in Safety phase",
            ]
        }
    except Exception as e:
        logger.error(f"Slope stability template failed: {e}")
        return {"status": "error", "message": str(e), "completed_steps": results}
