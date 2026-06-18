# test_image_gen.py - Place in project root
"""
Quick test script for image generation with GapGPT.
Run: python3 test_image_gen.py
"""
import asyncio
from openai import OpenAI

# ============================================
# CONFIGURE THESE VALUES
# ============================================
API_KEY = "sk-0FsvMZCv8ULe5XyudGIqcldiF46t3GFBWaUj3w6VrEYrq2lI"  # Replace with your actual API key
BASE_URL = "https://api.gapgpt.app/v1"

# Models to test
MODELS_TO_TEST = [
    "gapgpt/z-image",
    "imagen-4.0-fast-generate-001",
    "dall-e-3",
    "gemini-2.5-flash-image",
    "imagen-4.0-generate-001",
    "imagen-4.0-ultra-generate-001",
    "gemini-3.1-flash-image-preview",
    "gpt-image-1-mini",
    "gpt-image-2",
    "gpt-image-1.5",
    "gpt-image-1"
]

# Test prompt (Persian-friendly, matches your use case)
TEST_PROMPT = "A beautiful charcoal grill with glowing embers, professional food photography, warm lighting, Persian style barbecue setup"

# ============================================

async def test_image_generation(model: str, prompt: str):
    """Test image generation with a specific model (no size)"""
    print(f"\n{'─'*50}")
    print(f"🔧 Testing: {model}")

    client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=120)

    try:
        print(f"   Sending request...")
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            # No size parameter - let model decide
        )

        image_url = None
        if hasattr(response, 'data') and response.data and len(response.data) > 0:
            image_url = response.data[0].url

        if image_url:
            print(f"   ✅ SUCCESS!")
            print(f"   URL: {image_url[:120]}...")
            return True, image_url, None
        else:
            print(f"   ❌ No image URL in response")
            return False, None, "No image URL returned"

    except Exception as e:
        error_str = str(e)
        error_type = type(e).__name__

        # Determine error reason
        if "429" in error_str:
            reason = "Rate limited (too many requests)"
        elif "401" in error_str:
            reason = "Invalid API key"
        elif "403" in error_str:
            reason = "Access denied (model not available)"
        elif "404" in error_str:
            reason = "Endpoint not found (model doesn't exist)"
        elif "400" in error_str:
            reason = "Bad request"
        elif "timeout" in error_str.lower():
            reason = "Request timed out"
        else:
            reason = error_str[:150]

        print(f"   ❌ FAILED: {error_type}")
        print(f"   → {reason}")
        return False, None, reason


async def main():
    print("=" * 60)
    print("🖼️  GapGPT Image Generation Test")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-4:] if len(API_KEY) > 4 else ''}")
    print(f"Prompt: {TEST_PROMPT}")
    print(f"\nTesting {len(MODELS_TO_TEST)} models...")

    working_models = []
    failed_models = []

    for i, model in enumerate(MODELS_TO_TEST):
        success, url, error = await test_image_generation(model, TEST_PROMPT)

        if success:
            working_models.append({"model": model, "url": url})
        else:
            failed_models.append({"model": model, "error": error})

        # Wait between tests to avoid rate limits
        if i < len(MODELS_TO_TEST) - 1:
            wait = 3
            print(f"\n   ⏳ Waiting {wait}s before next test...")
            await asyncio.sleep(wait)

    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST RESULTS")
    print(f"{'='*60}")

    if working_models:
        print(f"\n✅ WORKING MODELS ({len(working_models)}):")
        for m in working_models:
            print(f"   ✅ {m['model']}")

    if failed_models:
        print(f"\n❌ FAILED MODELS ({len(failed_models)}):")
        for m in failed_models:
            print(f"   ❌ {m['model']}")
            print(f"      → {m['error']}")

    # Recommendations
    print(f"\n{'='*60}")
    print("💡 RECOMMENDATIONS")
    print(f"{'='*60}")

    if working_models:
        print(f"\nUse this in admin panel (/admin/ai-settings):")
        print(f"   Image Model: {working_models[0]['model']}")
        print(f"\nOther working options:")
        for m in working_models[1:]:
            print(f"   - {m['model']}")
    else:
        print(f"\n❌ No models worked!")
        print(f"\n🔍 Troubleshooting:")
        print(f"   1. Check API key is correct")
        print(f"   2. Check account has image generation credits")
        print(f"   3. Check base URL: {BASE_URL}")
        print(f"   4. Some models may need special access on GapGPT")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("⚠️  BEFORE RUNNING:")
    print("   1. Edit API_KEY at the top of this file")
    print("   2. Make sure you have image credits on GapGPT")
    print("=" * 60)
    print("\nPress Enter to start testing, or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled.")
        exit(0)

    asyncio.run(main())
