import os
import httpx
import logging
from .base import LLMProvider

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    def __init__(self):
        super().__init__("Claude")
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    async def generate_response(self, system_prompt: str, user_prompt: str):
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        await self._wait_for_cooldown()

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
            )
            response.raise_for_status()
            result = response.json()
            # Claude returns content as a list of blocks
            content_blocks = result.get("content", [])
            text_parts = [
                block["text"]
                for block in content_blocks
                if block.get("type") == "text"
            ]
            return "\n".join(text_parts)
