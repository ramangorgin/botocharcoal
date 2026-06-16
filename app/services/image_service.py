import os
import uuid
import httpx

from app.core.config import settings


async def download_image(url: str) -> tuple[str, str]:

    filename = f"{uuid.uuid4()}.png"

    local_path = os.path.join(settings.MEDIA_ROOT, filename)

    async with httpx.AsyncClient() as client:
        resp = await client.get(url)

    resp.raise_for_status()

    with open(local_path, "wb") as f:
        f.write(resp.content)

    public_url = f"{settings.MEDIA_URL}/{filename}"

    return local_path, public_url
