import json
import logging
from providers.gemini import GeminiProvider
from providers.groq import GroqProvider

logger = logging.getLogger(__name__)

class PlaxisAgent:
    def __init__(self):
        self.gemini = GeminiProvider()
        self.groq = GroqProvider()
        
        self.system_prompt = """
You are a Plaxis 3D Geotechnical Automation AI Agent.
Your job is to convert the user's natural language requests into a sequence of tool calls.

Available tools:
- create_borehole(x: float, y: float, layers: list)
- create_surface(points: list)
- extrude(object_name: str, direction: list, length: float)
- create_soil_material(name: str, model: str, params: dict)
- assign_material(object_name: str, material_name: str)
- create_plate(points: list)
- add_phase(name: str, phase_type: str)
- generate_mesh(fineness: float)
- run_calculation()

If you need to call tools, return ONLY a JSON block like:
```json
{
  "tool_calls": [
    {"name": "create_borehole", "args": {"x": 0, "y": 0, "layers": []}}
  ],
  "message": "I have created the borehole."
}
```
If no tools are needed, just return a JSON block with an empty `tool_calls` array and a `message`.
"""

    async def process_request(self, user_prompt: str):
        try:
            logger.info("Attempting with Gemini...")
            response = await self.gemini.generate_response(self.system_prompt, user_prompt)
        except Exception as e:
            logger.warning(f"Gemini failed ({e}), falling back to Groq...")
            response = await self.groq.generate_response(self.system_prompt, user_prompt)
            
        # Simplistic parsing of JSON response
        try:
            # try to extract JSON block if wrapped in markdown
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            parsed = json.loads(json_str)
            return parsed
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {"tool_calls": [], "message": f"LLM responded, but failed to parse: {response}"}

agent = PlaxisAgent()
