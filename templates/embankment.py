"""
Template: Embankment on Soft Soil with Consolidation
Creates an embankment model with:
- Soft clay foundation soil
- Staged embankment construction
- Consolidation analysis
"""
import logging
from plaxis_connection import connection_manager
from tools.geometry import create_borehole
from tools.materials import create_soil_material
from tools.phases import add_phase
from tools.mesh import generate_mesh

logger = logging.getLogger(__name__)

def run_embankment_template(
    embankment_height: float = 5.0,
    embankment_width: float = 30.0,
    slope_angle: float = 2.0,
    soft_layer_depth: float = 15.0,
):
    """
    Create an embankment on soft soil model with consolidation.

    Args:
        embankment_height: Height of embankment (m).
        embankment_width: Crest width of embankment (m).
        slope_angle: Slope ratio (H:V), e.g. 2.0 means 2H:1V.
        soft_layer_depth: Depth of soft clay layer (m).
    """
    results = []
    s, g = connection_manager.get_input()

    try:
        s.new()
        results.append("Created new project")

        # Soil layers: soft clay over stiff base
        layers = [
            {"top": 0, "bottom": -2},                    # Crust
            {"top": -2, "bottom": -soft_layer_depth},     # Soft clay
            {"top": -soft_layer_depth, "bottom": -25},    # Dense sand base
        ]
        create_borehole(0, 0, layers)
        results.append(f"Created stratigraphy (soft clay to {soft_layer_depth}m)")

        # Soil materials
        create_soil_material("Clay Crust", "Mohr-Coulomb", {
            "gammaUnsat": 17.0, "gammaSat": 18.0,
            "Eref": 8000, "nu": 0.35,
            "cref": 5.0, "phi": 22.0,
        })
        create_soil_material("Soft Clay", "Soft Soil", {
            "gammaUnsat": 15.0, "gammaSat": 17.0,
            "lambda": 0.15, "kappa": 0.03,
            "nu": 0.15,
            "cref": 2.0, "phi": 20.0,
            "kx": 1e-4, "ky": 1e-4,  # permeability for consolidation
        })
        create_soil_material("Dense Sand", "Mohr-Coulomb", {
            "gammaUnsat": 19.0, "gammaSat": 21.0,
            "Eref": 50000, "nu": 0.3,
            "cref": 0.0, "phi": 35.0,
        })
        results.append("Created soil materials (including Soft Soil model for clay)")

        # Embankment fill material
        create_soil_material("Embankment Fill", "Mohr-Coulomb", {
            "gammaUnsat": 18.0, "gammaSat": 20.0,
            "Eref": 20000, "nu": 0.3,
            "cref": 1.0, "phi": 30.0,
        })
        results.append("Created embankment fill material")

        # Create embankment geometry
        g.gotostructures()
        slope_run = embankment_height * slope_angle  # horizontal run of slope
        half_w = embankment_width / 2

        # Embankment cross-section as a trapezoidal surface
        emb_points = [
            -(half_w + slope_run), 0, 0,      # Left toe
            -half_w, 0, embankment_height,     # Left crest
            half_w, 0, embankment_height,      # Right crest
            (half_w + slope_run), 0, 0,        # Right toe
        ]
        try:
            g.surface(*emb_points)
            results.append(f"Created embankment geometry (H={embankment_height}m, W={embankment_width}m)")
        except Exception as e:
            results.append(f"Embankment geometry needs manual adjustment: {e}")

        # Mesh
        generate_mesh(0.5)
        results.append("Generated medium mesh")

        # Phases: staged construction with consolidation
        add_phase("Embankment Stage 1 (half height)", "Plastic")
        add_phase("Consolidation 1", "Consolidation")
        add_phase("Embankment Stage 2 (full height)", "Plastic")
        add_phase("Consolidation 2 (long term)", "Consolidation")
        add_phase("Safety Analysis", "Safety")
        results.append("Created 5 phases (staged fill + consolidation + safety)")

        return {
            "status": "success",
            "message": "Embankment template created successfully with consolidation analysis.",
            "details": results,
            "parameters": {
                "embankment_height": embankment_height,
                "embankment_width": embankment_width,
                "slope_angle": slope_angle,
                "soft_layer_depth": soft_layer_depth,
            }
        }
    except Exception as e:
        logger.error(f"Embankment template failed: {e}")
        return {"status": "error", "message": str(e), "completed_steps": results}
