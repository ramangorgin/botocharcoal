# app/services/ai_service.py
import json
import logging
import httpx
import aiofiles
import asyncio
import os
from pathlib import Path
from uuid import uuid4
from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional

from app.db.models.ai_settings import AISettings
from app.core.config import settings

# Set up logging
logger = logging.getLogger(__name__)

# Known working models for fallback
KNOWN_WORKING_MODELS = {
    "text": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "claude-3-5-sonnet",
        "gemini-2.5-pro",
        "deepseek-chat",
    ],
    "image": [
        "gapgpt/z-image",      # ✅ Cheapest & working - primary
        "dall-e-3",
        "gpt-image-1",
        "gpt-image-2",
        "dall-e-2",
    ]
}


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._client = None
        self._settings = None
        logger.info("🆕 AIService instance created")

    async def _get_client(self) -> OpenAI:
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            ai = await self.get_settings()

            logger.info("=" * 60)
            logger.info("🔧 INITIALIZING OPENAI CLIENT")
            logger.info(f"   Provider: {ai.provider}")
            logger.info(f"   Base URL: {ai.base_url}")
            logger.info(f"   Text Model: {ai.text_model}")
            logger.info(f"   Image Model: {ai.image_model}")
            logger.info(f"   API Key: {ai.api_key[:10]}...{ai.api_key[-4:] if len(ai.api_key) > 4 else 'N/A'}")
            logger.info(f"   API Key Length: {len(ai.api_key)}")

            # Clean and validate API key
            api_key = ai.api_key.strip()

            # Check for common issues
            issues_found = []
            if api_key != ai.api_key:
                issues_found.append("API key had leading/trailing whitespace")
            if '\n' in api_key or '\r' in api_key:
                issues_found.append("API key contains newline characters")
            if not api_key.startswith("sk-"):
                issues_found.append("API key doesn't start with 'sk-'")
            if len(api_key) < 20:
                issues_found.append(f"API key seems too short ({len(api_key)} chars)")

            if issues_found:
                logger.warning("⚠️  API KEY ISSUES FOUND:")
                for issue in issues_found:
                    logger.warning(f"   - {issue}")

            # Use environment variable as fallback
            if not api_key or len(api_key) < 10:
                from app.core.config import settings as app_settings
                fallback_key = getattr(app_settings, 'GAPGPT_API_KEY', '')
                if fallback_key:
                    logger.warning("⚠️  Using API key from environment variable as fallback")
                    api_key = fallback_key
                else:
                    raise ValueError("❌ No valid API key found in database or environment variables")

            # Create the client with increased timeout and retries
            logger.info(f"🚀 Creating OpenAI client with base_url={ai.base_url.strip()}")
            try:
                self._client = OpenAI(
                    base_url=ai.base_url.strip(),
                    api_key=api_key,
                    timeout=180.0,  # 3 minutes
                    max_retries=2,
                )
                logger.info("✅ OpenAI client created successfully")
            except Exception as e:
                logger.error(f"❌ Failed to create OpenAI client: {str(e)}")
                raise

        return self._client

    async def get_settings(self) -> AISettings:
        if self._settings is None:
            logger.info("📊 FETCHING AI SETTINGS FROM DATABASE")
            try:
                result = await self.db.execute(select(AISettings).limit(1))
                self._settings = result.scalar_one()
                logger.info(f"✅ Settings loaded - Provider: {self._settings.provider}, Base URL: {self._settings.base_url}")
            except Exception as e:
                logger.error(f"❌ Failed to fetch AI settings: {str(e)}")
                raise ValueError(f"No AI settings found in database. Please configure AI settings first.") from e
        return self._settings

    def _reset_client(self):
        """Reset client when settings change"""
        logger.info("🔄 Resetting OpenAI client due to settings change")
        self._client = None
        self._settings = None

    async def generate_text(self, user_prompt: str) -> dict:
        logger.info("=" * 60)
        logger.info("📝 GENERATING TEXT CONTENT")
        logger.info(f"   User Prompt: {user_prompt[:150]}...")

        try:
            ai = await self.get_settings()
            client = await self._get_client()

            system_prompt = ai.system_prompt or "You are a helpful AI assistant that creates blog posts and Instagram content in Persian."
            logger.info(f"   System Prompt: {system_prompt[:100]}...")
            logger.info(f"   Model: {ai.text_model}")

            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Handle model-specific requirements
            model = ai.text_model.lower()
            if any(name in model for name in ["gemma", "llama", "mistral"]):
                logger.info(f"   Model {model} may not support system messages, merging prompts")
                messages = [
                    {"role": "user", "content": f"System instructions: {system_prompt}\n\nUser request: {user_prompt}"}
                ]

            request_params = {
                "model": ai.text_model,
                "messages": messages,
                "temperature": 0.7,
            }

            logger.info(f"📤 SENDING REQUEST TO: {ai.base_url}/chat/completions")
            logger.info(f"   Request params: model={request_params['model']}, "
                       f"messages_count={len(request_params['messages'])}, "
                       f"temperature={request_params['temperature']}")

            response = client.chat.completions.create(**request_params)

            logger.info(f"✅ RESPONSE RECEIVED")
            logger.info(f"   Response ID: {response.id}")
            logger.info(f"   Model Used: {response.model}")

            content = response.choices[0].message.content
            logger.info(f"   Content Length: {len(content)} chars")
            logger.info(f"   Content Preview: {content[:200]}...")

            # Clean content - remove markdown code blocks
            cleaned_content = content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            if cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()

            try:
                parsed_content = json.loads(cleaned_content)
                logger.info("   ✅ Content parsed as JSON successfully")
                return parsed_content
            except json.JSONDecodeError:
                logger.info("   ℹ️  Content is not JSON, wrapping in default structure")
                return {
                    "title": "Generated Content",
                    "slug": "generated-content",
                    "body_html": content,
                    "summary": content[:200] if len(content) > 200 else content,
                    "instagram_caption": content[:2200] if len(content) > 2200 else content,
                    "hashtags": "#generated #content",
                    "content": content
                }

        except Exception as e:
            logger.error(f"❌ ERROR GENERATING TEXT: {type(e).__name__}: {str(e)}")
            raise

    async def generate_image(self, prompt: str, size: str = None) -> str:
        """
        Generate an image with rate limit handling and retries.
        Size is optional - model decides if not specified.
        Falls back to gapgpt/z-image if the configured model fails.
        """
        logger.info("=" * 60)
        logger.info("🖼️  GENERATING IMAGE")
        logger.info(f"   Prompt: {prompt[:150]}...")

        try:
            ai = await self.get_settings()
            client = await self._get_client()

            # Use configured image model - validate it
            image_model = ai.image_model.strip() if ai.image_model else "gapgpt/z-image"

            # Known working models in order of preference
            primary_models = ["gapgpt/z-image"]  # Cheapest, tested working
            fallback_models = ["dall-e-3", "gpt-image-1", "dall-e-2"]

            # If the configured model isn't in our known list, use gapgpt/z-image
            if image_model not in primary_models + fallback_models:
                logger.warning(f"⚠️  Image model '{image_model}' not recognized. Using gapgpt/z-image instead")
                image_model = "gapgpt/z-image"

            logger.info(f"   Model: {image_model}")

            # Build request params
            request_params = {
                "model": image_model,
                "prompt": prompt,
                "n": 1,
            }

            # Only add size if valid for the model
            if size:
                if image_model == "dall-e-3":
                    valid_sizes = ["1024x1024", "1024x1792", "1792x1024"]
                    if size in valid_sizes:
                        request_params["size"] = size
                        logger.info(f"   Size: {size}")
                    else:
                        logger.warning(f"   Size '{size}' not supported by {image_model}, ignoring")
                elif image_model in ["dall-e-2", "gpt-image-1", "gpt-image-2"]:
                    request_params["size"] = size
                    logger.info(f"   Size: {size}")
                # gapgpt/z-image doesn't need size - it decides

            logger.info(f"📤 Sending image generation request...")

            # Try primary model first, then fallbacks
            models_to_try = [image_model] + [m for m in fallback_models if m != image_model]

            for attempt_model in models_to_try:
                request_params["model"] = attempt_model

                # Retry with exponential backoff for rate limits
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        response = client.images.generate(**request_params)

                        image_url = None
                        if hasattr(response, 'data') and response.data and len(response.data) > 0:
                            image_url = response.data[0].url

                        if image_url:
                            logger.info(f"✅ IMAGE URL OBTAINED ({attempt_model}): {image_url[:100]}...")
                            return image_url
                        else:
                            logger.warning(f"   Model {attempt_model} returned no image URL")
                            break  # Try next model

                    except Exception as e:
                        error_str = str(e)

                        if "429" in error_str and attempt < max_retries - 1:
                            wait_time = (2 ** attempt) * 5
                            logger.warning(f"⏳ Rate limited (429). Waiting {wait_time}s before retry {attempt + 2}/{max_retries}...")
                            await asyncio.sleep(wait_time)
                        elif "400" in error_str and size and "size" in error_str.lower():
                            logger.warning("🔄 Size error - retrying without size...")
                            request_params.pop("size", None)
                            continue
                        elif "401" in error_str or "403" in error_str:
                            logger.error(f"   Authentication error with {attempt_model}")
                            break  # Try next model
                        elif "404" in error_str:
                            logger.warning(f"   Model {attempt_model} not found, trying next...")
                            break  # Try next model
                        else:
                            logger.warning(f"   Error with {attempt_model}: {error_str[:150]}")
                            break  # Try next model

            raise Exception("All image models failed")

        except Exception as e:
            logger.error(f"❌ ERROR GENERATING IMAGE: {type(e).__name__}: {str(e)[:300]}")
            raise

    async def generate_images(self, prompts: List[str], count: int = 1, size: str = None) -> List[str]:
        """Generate multiple images with delays between each"""
        logger.info("=" * 60)
        logger.info(f"🖼️  GENERATING MULTIPLE IMAGES")
        logger.info(f"   Number of prompts: {len(prompts)}")
        logger.info(f"   Images per prompt: {count}")

        images = []
        total_attempted = 0
        total_successful = 0

        for prompt_idx, prompt in enumerate(prompts, 1):
            logger.info(f"   Processing prompt {prompt_idx}/{len(prompts)}: {prompt[:100]}...")

            for img_count in range(1, count + 1):
                total_attempted += 1
                try:
                    logger.info(f"      Generating image {img_count}/{count}...")
                    image_url = await self.generate_image(prompt, size)
                    images.append(image_url)
                    total_successful += 1
                    logger.info(f"      ✅ Image {img_count} generated successfully")

                    # Small delay between images to avoid rate limits
                    if img_count < count:
                        await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"      ❌ Failed to generate image {img_count}: {str(e)[:200]}")
                    continue

        logger.info(f"📊 IMAGE GENERATION SUMMARY")
        logger.info(f"   Total attempted: {total_attempted}")
        logger.info(f"   Total successful: {total_successful}")
        logger.info(f"   Success rate: {(total_successful/total_attempted*100):.1f}%")

        return images


async def download_and_save_image(image_url: str, filename_prefix: str = "image") -> Optional[str]:
    """Download image from URL and save locally, return local path"""
    try:
        media_dir = Path("media/generated_images")
        media_dir.mkdir(parents=True, exist_ok=True)

        file_name = f"{filename_prefix}_{uuid4().hex[:12]}.png"
        file_path = media_dir / file_name

        logger.info(f"📥 Downloading image from: {image_url[:100]}...")

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(image_url)
            response.raise_for_status()

            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(response.content)

            logger.info(f"✅ Image downloaded to: {file_path}")
            return str(file_path)

    except Exception as e:
        logger.error(f"❌ Failed to download image: {str(e)}")
        return None


# Helper functions for backward compatibility
async def generate_content_with_ai(topic: str, instructions: str = "") -> Dict[str, Any]:
    """Helper function for generating content (used in tasks)"""
    logger.info("🔄 Using helper function generate_content_with_ai")

    from app.db.session import async_session

    async with async_session() as db:
        service = AIService(db)
        prompt = f"موضوع: {topic}"
        if instructions:
            prompt += f"\n\nدستورالعمل‌ها:\n{instructions}"

        logger.info(f"📝 Generating content for topic: {topic}")
        result = await service.generate_text(prompt)
        logger.info(f"✅ Content generated successfully")
        return result


async def generate_images_with_ai(prompts: List[str], count: int = 1, size: str = None) -> List[str]:
    """Helper function for generating images (used in tasks)"""
    logger.info("🔄 Using helper function generate_images_with_ai")

    from app.db.session import async_session

    async with async_session() as db:
        service = AIService(db)
        images = await service.generate_images(prompts, count, size)
        logger.info(f"✅ Generated {len(images)} images")
        return images
