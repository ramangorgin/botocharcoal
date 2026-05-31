import aiofiles
from pathlib import Path
from uuid import uuid4
from app.core.config import settings


async def save_upload(file_bytes: bytes, original_filename: str, subfolder: str = "uploads") -> tuple[str, str]:
    """Save uploaded file. Returns (local_path, public_url)."""
    suffix = Path(original_filename).suffix.lower()
    filename = f"{uuid4().hex}{suffix}"
    dest_dir = Path(settings.MEDIA_ROOT) / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename

    async with aiofiles.open(dest, "wb") as f:
        await f.write(file_bytes)

    public_url = f"{settings.BASE_URL}{settings.MEDIA_URL}{subfolder}/{filename}"
    return str(dest), public_url
