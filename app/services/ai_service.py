import json
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.ai_settings import AISettings
from app.core.config import settings


class AIService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_settings(self) -> AISettings:
        result = await self.db.execute(select(AISettings).limit(1))
        return result.scalar_one()

    async def generate_text(self, user_prompt: str) -> dict:

        ai = await self.get_settings()

        system_prompt = ai.system_prompt or settings.AI_FALLBACK_SYSTEM_PROMPT

        url = f"{ai.base_url}/chat/completions"

        payload = {
            "model": ai.text_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
        }

        headers = {
            "Authorization": f"Bearer {ai.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, json=payload)

        resp.raise_for_status()

        data = resp.json()

        content = data["choices"][0]["message"]["content"]

        return json.loads(content)

    async def generate_image(self, prompt: str, size="1024x1024") -> str:

        ai = await self.get_settings()

        url = f"{ai.base_url}/images/generations"

        payload = {
            "model": ai.image_model,
            "prompt": prompt,
            "size": size,
        }

        headers = {
            "Authorization": f"Bearer {ai.api_key},
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, json=payload)

        resp.raise_for_status()

        data = resp.json()

        return data["data"][0]["url"]
