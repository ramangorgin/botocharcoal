"""
Botocharcoal AI Image Generation Service
------------------------------------------
Generates images using OpenAI-compatible APIs (OpenAI DALL-E, 
or any API that follows the OpenAI Images API format).

Images are downloaded and saved to the local media storage.
"""

import io
import httpx
from pathlib import Path
from uuid import uuid4
from typing import Optional
from PIL import Image
from app.core.config import settings
from app.core.logging import logger
from app.core.constants import INSTAGRAM_IMAGE_SIZE, BLOG_COVER_SIZE


async def generate_image(prompt: str, size: tuple = (1024, 1024)) -> str:
    """
    Generate a single image and save it to media storage.
    
    Args:
        prompt: English image generation prompt
        size: Target size (width, height)
    
    Returns:
        Public URL of the generated image
    """
    logger.info("ai_image_generate", prompt_short=prompt[:80], size=size)
    
    from openai import AsyncOpenAI
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.db.models.ai_settings import AISettings
    
    ai_settings = None
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AISettings).limit(1))
        ai_settings = result.scalar_one_or_none()
    
    api_key = None
    api_base = None
    model = settings.IMAGE_MODEL
    img_size = "1024x1024"
    
    if ai_settings:
        if ai_settings.api_key:
            api_key = ai_settings.api_key
        if ai_settings.api_base_url:
            api_base = ai_settings.api_base_url
        if ai_settings.image_model:
            model = ai_settings.image_model
    
    if not api_key:
        api_key = settings.OPENAI_API_KEY
    
    if not api_key:
        raise ValueError("No image generation API key configured.")
    
    client_kwargs = {"api_key": api_key}
    if api_base:
        client_kwargs["base_url"] = api_base
    
    client = AsyncOpenAI(**client_kwargs)
    
    # Determine DALL-E size parameter
    dall_e_size = img_size
    if size[1] > size[0]:
        dall_e_size = "1024x1792"
    elif size[0] > size[1]:
        dall_e_size = "1792x1024"
    
    response = await client.images.generate(
        model=model,
        prompt=prompt,
        size=dall_e_size,
        quality="standard",
        n=1,
    )
    
    url = response.data[0].url
    if not url:
        raise ValueError("Image generation returned no URL")
    
    # Determine output directory
    out_dir = Path(settings.MEDIA_ROOT) / "jobs" / str(uuid4().hex[:8])
    out_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"image_{uuid4().hex[:8]}.png"
    local_path = out_dir / filename
    public_url = f"{settings.BASE_URL}/media/jobs/{out_dir.name}/{filename}"
    
    await _download_image(url, local_path)
    
    logger.info("ai_image_saved", url=public_url)
    return public_url


async def generate_and_save_images(
    prompts: list[str],
    job_id: int,
    role: str = "instagram",
) -> list[dict]:
    """
    Generate multiple images and save them to media storage.
    
    Args:
        prompts: List of image prompts
        job_id: Job ID for organizing files
        role: "instagram" or "blog_cover"
    
    Returns:
        List of dicts: {local_path, public_url, prompt, sort_order}
    """
    size = INSTAGRAM_IMAGE_SIZE if role == "instagram" else BLOG_COVER_SIZE
    
    out_dir = Path(settings.MEDIA_ROOT) / "jobs" / str(job_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    async def _one(prompt: str, idx: int) -> dict:
        public_url = await generate_image(prompt, size)
        # Extract filename from URL
        filename = public_url.split("/")[-1]
        local_path = str(out_dir / filename)
        
        return {
            "local_path": local_path,
            "public_url": public_url,
            "prompt": prompt,
            "sort_order": idx,
        }
    
    # Sequential to avoid rate-limit
    for i, p in enumerate(prompts):
        results.append(await _one(p, i))
    
    return results


async def _download_image(url: str, dest: Path) -> None:
    """Download an image from URL and save to disk."""
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url)
        response.raise_for_status()
        
        # Verify it's a valid image
        try:
            img = Image.open(io.BytesIO(response.content))
            img.verify()
        except Exception as e:
            logger.warning("image_validation_warning", error=str(e))
        
        dest.write_bytes(response.content)
