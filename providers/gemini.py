import os
import asyncio
from .base import LLMProvider
from google import genai

class GeminiProvider(LLMProvider):
    def __init__(self):
        super().__init__("Gemini")
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    async def generate_response(self, system_prompt: str, user_prompt: str):
        if not self.client:
            raise ValueError("GEMINI_API_KEY not set")

        self._wait_for_cooldown()

        # Run the synchronous Gemini SDK call in a thread pool
        # so it doesn't block the FastAPI async event loop
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model='gemini-2.5-flash',
            contents=[system_prompt, user_prompt],
        )
        return response.text
