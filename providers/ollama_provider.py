import httpx
import json
import logging
from typing import List, Dict, Any
from .base import LLMProvider

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    """
    Provider for local Ollama models (e.g., gemma:2b, gemma:7b).
    This sends requests to the local Ollama instance running on port 11434.
    """
    def __init__(self, model_name: str = "gemma:2b", host: str = "http://localhost:11434"):
        super().__init__("Ollama (Local)")
        self.model_name = model_name
        self.host = host.rstrip("/")
        # We use a longer timeout since local models can be slower, 
        # especially on initial load or lower-end hardware.
        self.client = httpx.Client(timeout=180.0)

    def is_configured(self) -> bool:
        # Check if Ollama is running and the model is available
        try:
            resp = self.client.get(f"{self.host}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return any(m.get("name", "").startswith(self.model_name) for m in models)
        except Exception:
            return False
        return False

    def get_response(self, prompt: str, system_prompt: str, tools: List[Dict[str, Any]] = None) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
        }
        
        # Format tools using the standard OpenAI format that Ollama natively supports
        if tools:
            formatted_tools = []
            for tool in tools:
                props = {k: {"type": v["type"], "description": v.get("description", "")} 
                        for k, v in tool.get("parameters", {}).items()}
                
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": {
                            "type": "object",
                            "properties": props,
                            "required": tool.get("required", [])
                        }
                    }
                })
            payload["tools"] = formatted_tools

        try:
            logger.info(f"Routing to local Ollama model: {self.model_name}")
            response = self.client.post(f"{self.host}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            
            message = data.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])

            # Reconstruct the tool call format expected by our tool dispatcher
            if tool_calls:
                result_blocks = []
                if content:
                    result_blocks.append(content)
                    
                for call in tool_calls:
                    fn = call.get("function", {})
                    fn_name = fn.get("name")
                    fn_args = fn.get("arguments", {})
                    # Add our internal structured format
                    result_blocks.append(f"<tool_call>\n{json.dumps({'name': fn_name, 'arguments': fn_args})}\n</tool_call>")
                    
                return "\n\n".join(result_blocks)
                
            return content
            
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise Exception(f"Failed to communicate with Local Ollama instance: {str(e)}")
