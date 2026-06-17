# test_gapgpt.py - Place this in /home/raman/Projects/botocharcoal/
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.session import async_session
from app.db.models.ai_settings import AISettings
from sqlalchemy import select
from openai import OpenAI

async def test_direct_api():
    """Test the API with hardcoded values from your working curl command"""
    # IMPORTANT: Replace this with the EXACT key that worked in curl
    api_key = "sk-0FsvMZCv8ULe5XyudGIqcldiF46t3GFBWaUj3w6VrEYrq2lI"  # <-- CHANGE THIS!
    base_url = "https://api.gapgpt.app/v1"
    
    print("🔧 Testing with direct values (like curl)...")
    print(f"   API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 4 else ''}")
    client = OpenAI(base_url=base_url, api_key=api_key)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": "Say hello in Persian"}
            ],
            temperature=0.7,
        )
        print(f"✅ Success! Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def test_database_api():
    """Test with values from database"""
    print("\n🔧 Testing with database values...")
    async with async_session() as db:
        result = await db.execute(select(AISettings).limit(1))
        ai = result.scalar_one()
        
        print(f"   provider: {ai.provider}")
        print(f"   base_url: {ai.base_url}")
        print(f"   text_model: {ai.text_model}")
        print(f"   api_key: {ai.api_key[:10]}...{ai.api_key[-4:] if len(ai.api_key) > 4 else ''}")
        print(f"   api_key length: {len(ai.api_key)}")
        print(f"   api_key repr (first 30 chars): {repr(ai.api_key[:30])}")
        
        # Check for hidden characters
        if '\n' in ai.api_key or '\r' in ai.api_key:
            print("⚠️  API key contains newline characters!")
        if ai.api_key != ai.api_key.strip():
            print("⚠️  API key has leading/trailing whitespace!")
        
        # Test with stripped key
        cleaned_key = ai.api_key.strip()
        client = OpenAI(base_url=ai.base_url.strip(), api_key=cleaned_key)
        
        try:
            response = client.chat.completions.create(
                model=ai.text_model,
                messages=[
                    {"role": "user", "content": "Say hello in Persian"}
                ],
                temperature=0.7,
            )
            print(f"✅ Success! Response: {response.choices[0].message.content}")
            return True
        except Exception as e:
            print(f"❌ Failed with database key: {e}")
            
            # Try with the key you know works
            print("\n🔧 Trying with the known working key instead...")
            known_key = "sk-YOUR-ACTUAL-API-KEY-HERE"  # <-- CHANGE THIS!
            client = OpenAI(base_url=ai.base_url.strip(), api_key=known_key)
            
            try:
                response = client.chat.completions.create(
                    model=ai.text_model,
                    messages=[
                        {"role": "user", "content": "Say hello in Persian"}
                    ],
                    temperature=0.7,
                )
                print(f"✅ Success with known key! Database key is the problem.")
                return False
            except Exception as e2:
                print(f"❌ Also failed with known key: {e2}")
                print("   Problem might be with base_url or model name")
                return False

if __name__ == "__main__":
    print("Testing GapGPT API connection...")
    print("=" * 50)
    
    # Test with direct values first
    direct_success = asyncio.run(test_direct_api())
    
    # Then test with database values
    db_success = asyncio.run(test_database_api())
    
    if direct_success and not db_success:
        print("\n" + "="*50)
        print("💡 PROBLEM IDENTIFIED!")
        print("   The API key in the database is different from the working key.")
        print("   Solutions:")
        print("   1. Check the .env file or form submission for extra spaces")
        print("   2. Re-enter the API key in the admin panel")
        print("   3. Check database encoding")
