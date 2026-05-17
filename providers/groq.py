import os
import httpx
from .base import LLMProvider

class GroqProvider(LLMProvider):
    def __init__(self):
        super().__init__("Groq")
        self.api_key = os.getenv("GROQ_API_KEY")

    async def generate_response(self, system_prompt: str, user_prompt: str):
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set")

        self._wait_for_cooldown()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
