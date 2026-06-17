# fix_model.py - Place in project root
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.session import async_session
from app.db.models.ai_settings import AISettings
from sqlalchemy import select, update

async def fix_model_name():
    async with async_session() as db:
        # Get current settings
        result = await db.execute(select(AISettings).limit(1))
        ai = result.scalar_one()
        
        print(f"Current text model: {ai.text_model}")
        print(f"Current image model: {ai.image_model}")
        
        # Update to known working model
        ai.text_model = "gpt-4o"
        # If image model is also potentially problematic, fix it too
        if ai.image_model not in ["dall-e-3", "gpt-image-2"]:
            ai.image_model = "gpt-image-2"
            print(f"Also updated image model to: gpt-image-2")
        
        await db.commit()
        print(f"✅ Updated text model to: gpt-4o")

if __name__ == "__main__":
    asyncio.run(fix_model_name())
