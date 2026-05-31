import httpx
from app.core.config import settings
from app.core.logging import logger

GRAPH_BASE = f"https://graph.facebook.com/{settings.GRAPH_API_VERSION}"


async def _post(path: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{GRAPH_BASE}{path}", data=data)
        r.raise_for_status()
        return r.json()


async def upload_carousel_item(image_url: str) -> str:
    """Upload a single image as a carousel item. Returns container ID."""
    data = {
        "image_url": image_url,
        "is_carousel_item": "true",
        "access_token": settings.IG_LONG_LIVED_ACCESS_TOKEN,
    }
    result = await _post(f"/{settings.IG_BUSINESS_ACCOUNT_ID}/media", data)
    return result["id"]


async def publish_carousel(
    image_urls: list[str],
    caption: str,
) -> str:
    """Upload carousel items, create container, publish. Returns Instagram media ID."""
    # Step 1: upload each item
    item_ids = []
    for url in image_urls:
        cid = await upload_carousel_item(url)
        item_ids.append(cid)
        logger.info("ig_item_uploaded", container_id=cid)

    # Step 2: create carousel container
    container = await _post(
        f"/{settings.IG_BUSINESS_ACCOUNT_ID}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(item_ids),
            "caption": caption,
            "access_token": settings.IG_LONG_LIVED_ACCESS_TOKEN,
        },
    )
    carousel_id = container["id"]

    # Step 3: publish
    result = await _post(
        f"/{settings.IG_BUSINESS_ACCOUNT_ID}/media_publish",
        {
            "creation_id": carousel_id,
            "access_token": settings.IG_LONG_LIVED_ACCESS_TOKEN,
        },
    )
    media_id = result["id"]
    logger.info("ig_carousel_published", media_id=media_id)
    return media_id
