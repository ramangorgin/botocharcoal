# app/services/ai_service.py
import json
import logging
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
        "dall-e-3",
        "gpt-image-2",
        "gpt-image-1",
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

            # Debug logging - Database values
            logger.info("=" * 60)
            logger.info("🔧 INITIALIZING OPENAI CLIENT")
            logger.info(f"   Provider: {ai.provider}")
            logger.info(f"   Base URL: {ai.base_url}")
            logger.info(f"   Text Model: {ai.text_model}")
            logger.info(f"   Image Model: {ai.image_model}")
            logger.info(f"   API Key: {ai.api_key[:10]}...{ai.api_key[-4:] if len(ai.api_key) > 4 else 'N/A'}")
            logger.info(f"   API Key Length: {len(ai.api_key)}")
            logger.info(f"   System Prompt: {ai.system_prompt[:100] if ai.system_prompt else 'None'}...")

            # Clean and validate API key
            api_key = ai.api_key.strip()

            # Check for common issues with API key
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

            # Use environment variable as fallback if database key seems invalid
            if not api_key or len(api_key) < 10:
                from app.core.config import settings as app_settings
                fallback_key = getattr(app_settings, 'GAPGPT_API_KEY', '')
                if fallback_key:
                    logger.warning("⚠️  Using API key from environment variable as fallback")
                    api_key = fallback_key
                else:
                    raise ValueError("❌ No valid API key found in database or environment variables")

            # Validate and fix model names
            text_model = ai.text_model.strip() if ai.text_model else "gpt-4o"
            if text_model not in KNOWN_WORKING_MODELS["text"]:
                logger.warning(f"⚠️  Text model '{text_model}' not in known working models list")
                logger.warning(f"   Will attempt to use it anyway, but consider switching to one of: {KNOWN_WORKING_MODELS['text']}")

            # Create the client
            logger.info(f"🚀 Creating OpenAI client with base_url={ai.base_url.strip()}, model={text_model}")
            try:
                self._client = OpenAI(
                    base_url=ai.base_url.strip(),
                    api_key=api_key,
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

                # Log full settings for debugging (mask sensitive data)
                logger.debug(f"   Full settings: provider={self._settings.provider}, "
                           f"base_url={self._settings.base_url}, "
                           f"text_model={self._settings.text_model}, "
                           f"image_model={self._settings.image_model}, "
                           f"api_key_masked={self._settings.api_key[:10]}...")

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

            # Prepare system prompt
            system_prompt = ai.system_prompt or "You are a helpful AI assistant that creates blog posts and Instagram content in Persian."
            logger.info(f"   System Prompt: {system_prompt[:100]}...")
            logger.info(f"   Model: {ai.text_model}")

            # Prepare messages based on model compatibility
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

            # Prepare request parameters
            request_params = {
                "model": ai.text_model,
                "messages": messages,
                "temperature": 0.7,
            }

            logger.info(f"📤 SENDING REQUEST TO: {ai.base_url}/chat/completions")
            logger.info(f"   Request params: model={request_params['model']}, "
                       f"messages_count={len(request_params['messages'])}, "
                       f"temperature={request_params['temperature']}")

            # Make the API call
            response = client.chat.completions.create(**request_params)

            # Log success
            logger.info(f"✅ RESPONSE RECEIVED")
            logger.info(f"   Response ID: {response.id}")
            logger.info(f"   Model Used: {response.model}")
            logger.info(f"   Usage: {response.usage}")

            content = response.choices[0].message.content
            logger.info(f"   Content Length: {len(content)} chars")
            logger.info(f"   Content Preview: {content[:200]}...")

            # Try to parse as JSON if it's a JSON string
            try:
                parsed_content = json.loads(content)
                logger.info("   ✅ Content parsed as JSON successfully")
                logger.debug(f"   JSON keys: {list(parsed_content.keys())}")
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
            logger.error(f"❌ ERROR GENERATING TEXT")
            logger.error(f"   Error Type: {type(e).__name__}")
            logger.error(f"   Error Message: {str(e)}")

            if hasattr(e, 'response'):
                try:
                    logger.error(f"   HTTP Status: {e.response.status_code}")
                    logger.error(f"   Response Body: {e.response.text[:500]}")
                except:
                    pass

            if hasattr(e, 'body'):
                try:
                    logger.error(f"   Error Body: {e.body}")
                except:
                    pass

            # Provide helpful debug info
            if "403" in str(e):
                logger.error("   🔍 403 ERROR ANALYSIS:")
                logger.error("   - Check if the model name is correct and available")
                logger.error("   - Check if your API key has access to this model")
                logger.error(f"   - Known working models: {KNOWN_WORKING_MODELS['text']}")
            elif "401" in str(e):
                logger.error("   🔍 401 ERROR ANALYSIS:")
                logger.error("   - API key might be invalid or expired")
                logger.error("   - Check if the API key has sufficient credits")

            raise

    async def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        logger.info("=" * 60)
        logger.info("🖼️  GENERATING IMAGE")
        logger.info(f"   Prompt: {prompt[:150]}...")
        logger.info(f"   Size: {size}")

        try:
            ai = await self.get_settings()
            client = await self._get_client()

            logger.info(f"   Model: {ai.image_model}")
            logger.info(f"📤 Sending image generation request to: {ai.base_url}/images/generations")

            # Validate image model
            image_model = ai.image_model.strip() if ai.image_model else "gpt-image-2"
            if image_model not in KNOWN_WORKING_MODELS["image"]:
                logger.warning(f"⚠️  Image model '{image_model}' not in known working models list")

            response = client.images.generate(
                model=image_model,
                prompt=prompt,
                size=size,
                n=1,
            )

            image_url = response.data[0].url
            logger.info(f"✅ IMAGE GENERATED SUCCESSFULLY")
            logger.info(f"   Image URL: {image_url[:100]}...")

            return image_url

        except Exception as e:
            logger.error(f"❌ ERROR GENERATING IMAGE")
            logger.error(f"   Error Type: {type(e).__name__}")
            logger.error(f"   Error Message: {str(e)}")

            if hasattr(e, 'response'):
                try:
                    logger.error(f"   HTTP Status: {e.response.status_code}")
                    logger.error(f"   Response Body: {e.response.text[:500]}")
                except:
                    pass

            raise

    async def generate_images(self, prompts: List[str], count: int = 1, size: str = "1024x1024") -> List[str]:
        """Generate multiple images"""
        logger.info("=" * 60)
        logger.info(f"🖼️  GENERATING MULTIPLE IMAGES")
        logger.info(f"   Number of prompts: {len(prompts)}")
        logger.info(f"   Images per prompt: {count}")
        logger.info(f"   Total images to generate: {len(prompts) * count}")
        logger.info(f"   Size: {size}")

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
                except Exception as e:
                    logger.error(f"      ❌ Failed to generate image {img_count}: {str(e)[:200]}")
                    # Continue with other images even if one fails
                    continue

        logger.info(f"📊 IMAGE GENERATION SUMMARY")
        logger.info(f"   Total attempted: {total_attempted}")
        logger.info(f"   Total successful: {total_successful}")
        logger.info(f"   Success rate: {(total_successful/total_attempted*100):.1f}%")

        return images


# Helper functions for backward compatibility
async def generate_content_with_ai(topic: str, instructions: str = "") -> Dict[str, Any]:
    """Helper function for generating content (used in tasks)"""
    logger.info("🔄 Using helper function generate_content_with_ai")

    from app.db.session import async_session
    from app.services.ai_service import AIService

    async with async_session() as db:
        service = AIService(db)
        prompt = f"موضوع: {topic}"
        if instructions:
            prompt += f"\nدستورالعمل‌ها: {instructions}"

        logger.info(f"📝 Generating content for topic: {topic}")
        result = await service.generate_text(prompt)
        logger.info(f"✅ Content generated successfully")
        return result


async def generate_images_with_ai(prompts: List[str], count: int = 1, size: str = "1024x1024") -> List[str]:
    """Helper function for generating images (used in tasks)"""
    logger.info("🔄 Using helper function generate_images_with_ai")

    from app.db.session import async_session
    from app.services.ai_service import AIService

    async with async_session() as db:
        service = AIService(db)
        images = await service.generate_images(prompts, count, size)
        logger.info(f"✅ Generated {len(images)} images")
        return images
