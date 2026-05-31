import asyncio
from pathlib import Path
from uuid import uuid4
import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.core.logging import logger
from app.core.constants import INSTAGRAM_IMAGE_SIZE, BLOG_COVER_SIZE

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=30))
async def _generate_url(prompt: str, dall_e_size: str) -> str:
    response = await client.images.generate(
        model=settings.IMAGE_MODEL,
        prompt=prompt,
        size=dall_e_size,
        quality="standard",
        n=1,
    )
    return response.data[0].url


async def _download(url: str, dest: Path) -> None:
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)


async def generate_and_save_images(
    prompts: list[str],
    job_id: int,
    role: str,          # "instagram" | "blog_cover"
    media_root: str,
    base_url: str,
) -> list[dict]:
    """
    Returns list of dicts: {local_path, public_url, prompt, sort_order}
    """
    size = INSTAGRAM_IMAGE_SIZE if role == "instagram" else BLOG_COVER_SIZE
    dall_e_size = "1024x1792" if size[1] > size[0] else "1792x1024"

    out_dir = Path(media_root) / "jobs" / str(job_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    async def _one(prompt: str, idx: int) -> dict:
        url = await _generate_url(prompt, dall_e_size)
        filename = f"{role}_{idx}_{uuid4().hex[:8]}.png"
        local_path = out_dir / filename
        await _download(url, local_path)
        public_url = f"{base_url}/media/jobs/{job_id}/{filename}"
        logger.info("image_saved", role=role, idx=idx, path=str(local_path))
        return {
            "local_path": str(local_path),
            "public_url": public_url,
            "prompt": prompt,
            "sort_order": idx,
        }

    # Sequential to avoid rate-limit; change to gather for speed if quota allows
    results = []
    for i, p in enumerate(prompts):
        results.append(await _one(p, i))
    return results
