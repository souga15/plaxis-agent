import os
import asyncio
import logging
from .base import LLMProvider

logger = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    def __init__(self):
        super().__init__("Gemini")
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except ImportError:
                logger.warning(
                    "google-genai package is not installed. "
                    "Gemini provider will be unavailable. "
                    "Install with: pip install google-genai"
                )

    async def generate_response(self, system_prompt: str, user_prompt: str):
        if not self.client:
            raise ValueError(
                "Gemini provider is not available. "
                "Check that GEMINI_API_KEY is set and google-genai is installed."
            )

        await self._wait_for_cooldown()

        # Run the synchronous Gemini SDK call in a thread pool
        # so it doesn't block the FastAPI async event loop
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model='gemini-2.5-flash',
            contents=[system_prompt, user_prompt],
        )
        return response.text
