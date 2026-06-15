"""
Botocharcoal AI Text Generation Service
---------------------------------------
Generates Persian blog and Instagram content using OpenAI-compatible APIs.
"""

import json
from typing import Any
from slugify import slugify
from app.core.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.db.models.ai_settings import AISettings
from sqlalchemy import select


DEFAULT_PROMPTS = {
    "post_row": {
        "system": (
            "تو یک نویسنده و استراتژیست تولید محتوا برای برند بتوچارکول هستی. "
            "خروجی باید دقیقاً ساختار یک ردیف جدول posts باشد و شامل اطلاعات وبلاگ و اینستاگرام باشد."
        ),
        "template": (
            "بر اساس موضوع زیر، خروجی را فقط و فقط به صورت JSON بده.\n\n"
            "موضوع: {subject}\n"
            "{instructions}\n\n"
            "JSON باید دقیقا این فیلدها را داشته باشد:\n"
            "{\n"
            '  "topic": "...",\n'
            '  "title": "...",\n'
            '  "slug": "...",\n'
            '  "body_html": "...",\n'
            '  "summary": "...",\n'
            '  "category": "...",\n'
            '  "cover_image_url": null,\n'
            '  "publish_date": null,\n'
            '  "instagram_caption": "...",\n'
            '  "hashtags": "#a #b #c",\n'
            '  "meta_title": "...",\n'
            '  "meta_description": "...",\n'
            '  "og_title": "...",\n'
            '  "og_description": "...",\n'
            '  "og_image": null,\n'
            '  "blog_enabled": true,\n'
            '  "instagram_enabled": true\n'
            "}\n\n"
            "قواعد:\n"
            "- body_html باید HTML معتبر باشد.\n"
            "- slug باید لاتین و مناسب URL باشد.\n"
            "- publish_date را null بگذار.\n"
            "- cover_image_url و og_image را null بگذار مگر اینکه URL معتبر لازم باشد.\n"
            "- هیچ متن اضافه‌ای خارج از JSON برنگردان."
        ),
    },
    "image_prompt": {
        "system": (
            "You are a prompt engineer for product and lifestyle image generation "
            "for a premium charcoal brand."
        ),
        "template": (
            "Create an English prompt for image generation.\n"
            "Subject: {subject}\n"
            "{instructions}\n"
            "Style: premium charcoal, barbecue, warm embers, realistic photography.\n"
            "Output only prompt text."
        ),
    },
}


def _get_system_prompt(key: str) -> str:
    return DEFAULT_PROMPTS[key]["system"]


def _get_user_prompt(key: str, subject: str, instructions: str = "") -> str:
    template = DEFAULT_PROMPTS[key]["template"]
    instr = f"دستورالعمل اضافی:\n{instructions}" if instructions else ""
    return template.format(subject=subject, instructions=instr)


async def generate_post_row(subject: str, instructions: str = "") -> dict[str, Any]:
    """
    Generate a full post-row payload compatible with posts table.
    """
    logger.info("ai_text_generate_post_row", subject=subject)
    messages = [
        {"role": "system", "content": _get_system_prompt("post_row")},
        {"role": "user", "content": _get_user_prompt("post_row", subject, instructions)},
    ]
    response = await _call_text_api(messages, response_format=True)
    raw = response.choices[0].message.content

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        title = subject.strip()[:120] or "پست جدید"
        data = {
            "topic": subject,
            "title": title,
            "slug": slugify(title) or slugify(subject) or "post",
            "body_html": f"<h2>{title}</h2><p>{raw[:1000]}</p>",
            "summary": raw[:280] if raw else "",
            "category": None,
            "cover_image_url": None,
            "publish_date": None,
            "instagram_caption": raw[:600] if raw else "",
            "hashtags": "",
            "meta_title": title[:60],
            "meta_description": (raw[:155] if raw else title),
            "og_title": title,
            "og_description": raw[:200] if raw else title,
            "og_image": None,
            "blog_enabled": True,
            "instagram_enabled": True,
        }

    title = (data.get("title") or subject or "پست جدید").strip()
    data["topic"] = (data.get("topic") or subject or title).strip()
    data["title"] = title
    data["slug"] = slugify(data.get("slug") or title or subject or "post")
    data["body_html"] = data.get("body_html") or ""
    data["summary"] = data.get("summary") or None
    data["category"] = data.get("category") or None
    data["cover_image_url"] = data.get("cover_image_url") or None
    data["publish_date"] = data.get("publish_date") or None
    data["instagram_caption"] = data.get("instagram_caption") or None
    data["hashtags"] = data.get("hashtags") or None
    data["meta_title"] = data.get("meta_title") or None
    data["meta_description"] = data.get("meta_description") or None
    data["og_title"] = data.get("og_title") or None
    data["og_description"] = data.get("og_description") or None
    data["og_image"] = data.get("og_image") or None
    data["blog_enabled"] = bool(data.get("blog_enabled", True))
    data["instagram_enabled"] = bool(data.get("instagram_enabled", True))
    return data


async def generate_image_prompt(subject: str, instructions: str = "") -> str:
    logger.info("ai_text_generate_image_prompt", subject=subject)
    messages = [
        {"role": "system", "content": _get_system_prompt("image_prompt")},
        {"role": "user", "content": _get_user_prompt("image_prompt", subject, instructions)},
    ]
    response = await _call_text_api(messages)
    return response.choices[0].message.content.strip()


async def _call_text_api(messages: list[dict[str, str]], response_format: bool = False):
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise RuntimeError("openai package not installed") from exc

    ai_settings = None
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AISettings).limit(1))
        ai_settings = result.scalar_one_or_none()

    model = settings.TEXT_MODEL
    api_key = settings.OPENAI_API_KEY or None
    api_base = None

    if ai_settings:
        if ai_settings.api_key:
            api_key = ai_settings.api_key
        if ai_settings.api_base_url:
            api_base = ai_settings.api_base_url
        if ai_settings.text_model:
            model = ai_settings.text_model

    if not api_key:
        raise ValueError("No API key configured. Configure AI settings first.")

    client_kwargs: dict[str, str] = {"api_key": api_key}
    if api_base:
        client_kwargs["base_url"] = api_base

    client = AsyncOpenAI(**client_kwargs)
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.5,
    }
    if response_format:
        kwargs["response_format"] = {"type": "json_object"}
    return await client.chat.completions.create(**kwargs)
