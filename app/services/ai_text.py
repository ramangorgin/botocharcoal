"""
Botocharcoal AI Text Generation Service
----------------------------------------
Generates Persian blog posts, Instagram captions, and hashtags
using OpenAI-compatible APIs (OpenAI, Anthropic, or custom providers).
"""

import json
from typing import Optional
from slugify import slugify
from app.core.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.db.models.ai_settings import AISettings
from sqlalchemy import select


DEFAULT_PROMPTS = {
    "blog_text": {
        "system": (
            "تو یک نویسنده و متخصص سئو فارسی برای برند 'بتوچارکول' هستی. "
            "تخصص تو تولید محتوای ارزشمند درباره ذغال، باربیکیو، پیک نیک، "
            "کباب و سبک زندگی outdoors است. "
            "محتوایی که می‌نویسی باید: "
            "۱. کاملاً طبیعی و انسانی باشد (نه هوش مصنوعی) "
            "۲. دارای ساختار SEO-friendly باشد (تگ‌های H2/H3 مناسب، پاراگراف کوتاه) "
            "۳. شامل مقدمه جذاب، بدنه مفید، و نتیجه‌گیری باشد "
            "۴. کلمات کلیدی مرتبط با ذغال و باربیکیو را به‌طور طبیعی بگنجاند "
            "۵. از ادعاهای پزشکی یا قیمت‌گذاری خودداری کند"
        ),
        "template": (
            "یک مقاله وب فارسی درباره موضوع زیر تولید کن:\n\n"
            "موضوع: {subject}\n"
            "{instructions}\n\n"
            "خروجی باید دقیقاً به فرمت JSON زیر باشد:\n"
            '{{\n'
            '  "title": "عنوان فارسی جذاب و SEO-friendly (حداکثر ۷۰ کاراکتر)",\n'
            '  "slug": "slug-latin-en-ke-ja-ta-esh-ba-esh-e-farsi-translated.shod",\n'
            '  "body_html": "<h2>مقدمه</h2>\\n<p>متن مقدمه...</p>\\n\\n"\n'
            '    "<h2>بخش اول</h2>\\n<p>...</p>\\n\\n"\n'
            '    "<h2>بخش دوم</h2>\\n<p>...</p>\\n\\n"\n'
            '    "<h2>سؤالات متداول</h2>\\n<p>...</p>\\n\\n"\n'
            '    "<h2>نتیجه‌گیری</h2>\\n<p>...</p>"\n'
            '}}\n\n'
            "توجه:\n"
            "- body_html باید HTML معتبر باشد (markdown نه)\n"
            "- حداقل ۳ بخش با H2 داشته باشد\n"
            "- شامل بخش FAQ باشد"
        ),
    },
    "instagram_caption": {
        "system": (
            "تو یک متخصص شبکه‌های اجتماعی برای برند 'بتوچارکول' هستی. "
            "تخصص تو نوشتن کپشن اینستاگرام فارسی جذاب است. "
            "کپشن باید: "
            "۱. با یک هوک قوی شروع شود (سؤال، واقعیت جالب، یا ادعای جذاب) "
            "۲. مزایای محصول/موضوع را برجسته کند "
            "۳. لحن گرم، صمیمی، و حرفه‌ای داشته باشد "
            "۴. شامل CTA واضح باشد "
            "۵. بین ۸۰ تا ۲۰۰ کلمه باشد"
        ),
        "template": (
            "یک کپشن اینستاگرام فارسی درباره موضوع زیر تولید کن:\n\n"
            "موضوع: {subject}\n"
            "{instructions}\n\n"
            "خروجی فقط متن کپشن باشد (بدون JSON)."
        ),
    },
    "instagram_hashtags": {
        "system": (
            "تو یک متخصص هشتگ اینستاگرام فارسی هستی. "
            "هشتگ‌های مرتبط و پربازدید برای موضوعاتی درباره ذغال، باربیکیو، "
            "کباب، پیک نیک و سبک زندگی outdoors تولید کن."
        ),
        "template": (
            "بین ۱۵ تا ۲۵ هشتگ فارسی و انگلیسی مرتبط با موضوع زیر تولید کن:\n\n"
            "موضوع: {subject}\n"
            "{instructions}\n\n"
            "خروجی فقط هشتگ‌ها باشد، هر هشتگ در یک خط (بدون JSON)."
        ),
    },
    "image_prompt": {
        "system": (
            "You are a prompt engineer for DALL-E image generation. "
            "Create vivid, detailed English image prompts for a premium charcoal brand "
            "(Botocharcoal) that sells high-quality charcoal for barbecue and outdoor cooking."
        ),
        "template": (
            "Create a detailed image generation prompt in English. "
            "The image is for a premium Iranian charcoal brand called 'Botocharcoal'. "
            "Subject: {subject}\n"
            "{instructions}\n\n"
            "Style: Premium product photography, dark moody industrial aesthetic, "
            "warm ember lighting, high contrast, professional food photography style. "
            "Output ONLY the prompt text, no explanations."
        ),
    },
}


def _get_system_prompt(key: str) -> str:
    """Return the system prompt for a given key."""
    return DEFAULT_PROMPTS[key]["system"]


def _get_user_prompt(key: str, subject: str, instructions: str = "") -> str:
    """Return the user prompt for a given key with subject/instructions filled in."""
    template = DEFAULT_PROMPTS[key]["template"]
    instr = f"دستورالعمل اضافی:\n{instructions}" if instructions else ""
    return template.format(subject=subject, instructions=instr)


async def generate_blog_text(subject: str, instructions: str = "") -> dict:
    """
    Generate a complete Persian blog post.
    
    Returns:
        dict with keys: title, slug, body_html
    """
    logger.info("ai_text_generate_blog", subject=subject)
    
    messages = [
        {"role": "system", "content": _get_system_prompt("blog_text")},
        {"role": "user", "content": _get_user_prompt("blog_text", subject, instructions)},
    ]
    
    response = await _call_text_api(messages, response_format=True)
    raw = response.choices[0].message.content
    
    try:
        data = json.loads(raw)
        title = data.get("title", subject)
        slug = data.get("slug", slugify(title))
        body_html = data.get("body_html", "")
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("ai_text_parse_fallback", error=str(e))
        title = subject
        slug = slugify(subject)
        body_html = f"<h2>{subject}</h2>\n<p>{raw[:500]}...</p>"
    
    result = {"title": title, "slug": slug, "body_html": body_html}
    logger.info("ai_text_blog_generated", title=title, slug=slug)
    return result


async def generate_instagram_caption(subject: str, instructions: str = "") -> str:
    """Generate a Persian Instagram caption."""
    logger.info("ai_text_generate_caption", subject=subject)
    
    messages = [
        {"role": "system", "content": _get_system_prompt("instagram_caption")},
        {"role": "user", "content": _get_user_prompt("instagram_caption", subject, instructions)},
    ]
    
    response = await _call_text_api(messages)
    caption = response.choices[0].message.content.strip()
    
    logger.info("ai_text_caption_generated", length=len(caption))
    return caption


async def generate_instagram_hashtags(subject: str, instructions: str = "") -> str:
    """Generate Persian/English hashtags for Instagram."""
    logger.info("ai_text_generate_hashtags", subject=subject)
    
    messages = [
        {"role": "system", "content": _get_system_prompt("instagram_hashtags")},
        {"role": "user", "content": _get_user_prompt("instagram_hashtags", subject, instructions)},
    ]
    
    response = await _call_text_api(messages)
    hashtags_raw = response.choices[0].message.content.strip()
    
    # Clean up: ensure all start with #
    hashtags = []
    for line in hashtags_raw.split("\n"):
        line = line.strip().strip("*-•").strip()
        if line and not line.startswith("#"):
            line = "#" + line
        if line:
            hashtags.append(line)
    
    result = " ".join(hashtags)
    logger.info("ai_text_hashtags_generated", count=len(hashtags))
    return result


async def generate_image_prompt(subject: str, instructions: str = "") -> str:
    """Generate an English image prompt for DALL-E."""
    logger.info("ai_text_generate_image_prompt", subject=subject)
    
    messages = [
        {"role": "system", "content": _get_system_prompt("image_prompt")},
        {"role": "user", "content": _get_user_prompt("image_prompt", subject, instructions)},
    ]
    
    response = await _call_text_api(messages)
    prompt = response.choices[0].message.content.strip()
    
    logger.info("ai_text_image_prompt_generated")
    return prompt


async def _call_text_api(messages: list, response_format: bool = False) -> "ChatCompletion":
    """
    Call the text generation API based on AISettings or fallback to config.
    """
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.error("openai_not_installed")
        raise RuntimeError("openai package not installed")
    
    # Try to load AISettings first
    ai_settings = None
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AISettings).limit(1))
        ai_settings = result.scalar_one_or_none()
    
    api_key = None
    api_base = None
    model = settings.TEXT_MODEL
    
    if ai_settings:
        if ai_settings.api_key:
            api_key = ai_settings.api_key
        if ai_settings.api_base_url:
            api_base = ai_settings.api_base_url
        if ai_settings.text_model:
            model = ai_settings.text_model
    else:
        # Fallback: create default AISettings
        ai_settings = AISettings(
            provider=settings.OPENAI_API_KEY and "openai" or "custom",
            api_key=settings.OPENAI_API_KEY,
            text_model=settings.TEXT_MODEL,
        )
        db.add(ai_settings)
        await db.commit()
        api_key = ai_settings.api_key
        model = ai_settings.text_model or settings.TEXT_MODEL
    
    if not api_key:
        raise ValueError("No API key configured. Set OPENAI_API_KEY in .env or configure in AI Settings.")
    
    client_kwargs = {"api_key": api_key}
    if api_base:
        client_kwargs["base_url"] = api_base
    
    client = AsyncOpenAI(**client_kwargs)
    
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
    }
    
    if response_format:
        kwargs["response_format"] = {"type": "json_object"}
    
    response = await client.chat.completions.create(**kwargs)
    return response
