import time
import asyncio
import logging

logger = logging.getLogger(__name__)

class LLMProvider:
    def __init__(self, name: str):
        self.name = name
        self.last_call_time = 0
        self.cooldown = 1.0 # default cooldown in seconds

    async def _wait_for_cooldown(self):
        elapsed = time.time() - self.last_call_time
        if elapsed < self.cooldown:
            await asyncio.sleep(self.cooldown - elapsed)
        self.last_call_time = time.time()

    async def generate_response(self, system_prompt: str, user_prompt: str):
        """Must be overridden by subclasses."""
        raise NotImplementedError
