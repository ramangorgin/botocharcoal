# app/db/migrations/add_separate_instructions.py
"""
Migration script to add separate instruction columns to jobs table.
Run this once to update your database schema.
"""
import asyncio
from sqlalchemy import text
from app.db.session import async_session, engine

async def run_migration():
    """Add new columns to jobs table"""
    async with engine.begin() as conn:
        # Check if columns already exist
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='jobs' AND column_name='blog_text_instructions'
        """))
        
        if result.fetchone():
            print("✅ Columns already exist, skipping migration")
            return
        
        print("📊 Running migration: Adding separate instruction columns...")
        
        # Add new columns
        await conn.execute(text("""
            ALTER TABLE jobs 
            ADD COLUMN blog_text_instructions TEXT,
            ADD COLUMN blog_image_instructions TEXT,
            ADD COLUMN instagram_text_instructions TEXT,
            ADD COLUMN instagram_image_instructions TEXT
        """))
        
        # Migrate existing data
        await conn.execute(text("""
            UPDATE jobs 
            SET blog_text_instructions = text_instructions,
                blog_image_instructions = image_instructions
            WHERE text_instructions IS NOT NULL OR image_instructions IS NOT NULL
        """))
        
        print("✅ Migration completed successfully!")
        print("   Added columns:")
        print("   - blog_text_instructions")
        print("   - blog_image_instructions")
        print("   - instagram_text_instructions")
        print("   - instagram_image_instructions")

if __name__ == "__main__":
    asyncio.run(run_migration())
