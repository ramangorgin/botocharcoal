# test_models.py - Place in project root
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from openai import OpenAI

async def test_models():
    # Use the exact key that works
    api_key = "sk-0FsvMZCv8ULe5XyudGIqcldiF46q2lI"  # Your actual working key
    base_url = "https://api.gapgpt.app/v1"
    
    # List of models to test
    models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo", 
        "gpt-3.5-turbo",
        "gemma-3-27b-it",
        "gemma-2-9b-it",
        "claude-3-5-sonnet",
        "deepseek-chat",
	"gapgpt/z-image",
	"gpt-5-nano"
    ]
    
    client = OpenAI(base_url=base_url, api_key=api_key)
    
    print("Testing different models...")
    print("=" * 60)
    
    for model in models:
        try:
            print(f"\n🔧 Testing model: {model}...")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": "Say 'hello' in one word"}
                ],
                temperature=0.7,
            )
            print(f"   ✅ SUCCESS: {response.choices[0].message.content}")
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "401" in error_msg:
                print(f"   ❌ Auth/Model Error: This model might not be available")
            else:
                print(f"   ❌ Error: {error_msg[:100]}")

if __name__ == "__main__":
    asyncio.run(test_models())
