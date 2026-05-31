import json
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.core.logging import logger

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """تو یک متخصص تولید محتوای فارسی برای برند ذغال‌فروشی بتوچارکول هستی.
محتوا باید حرفه‌ای، طبیعی، و مناسب مخاطب ایرانی باشد.
هیچ ادعای پزشکی، قیمت‌گذاری، یا اطلاعات نادرست ارائه نده."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def generate_text_pack(topic: str, tone: str | None, cta_text: str | None, image_count: int) -> dict:
    tone_str = tone or "حرفه‌ای و گرم"
    cta_str = cta_text or "برای سفارش با ما تماس بگیرید"

    prompt = f"""موضوع: {topic}
لحن: {tone_str}
CTA: {cta_str}
تعداد تصاویر اینستاگرام: {image_count}

یک پکیج محتوای کامل به فرمت JSON تولید کن با این فیلدها:
{{"blog_title": "عنوان جذاب و SEO-friendly فارسی",
  "blog_slug": "latin-slug-for-url",
  "blog_body": "متن کامل مقاله فارسی با ساختار HTML (h2, p, ul, li) - شامل مقدمه، ۳ تا ۵ بخش با عنوان، بخش FAQ، و نتیجه‌گیری",
  "instagram_caption": "کپشن اینستاگرام فارسی با هوک قوی، مزایای محصول، و CTA",
  "hashtags": "هشتگ‌های فارسی و انگلیسی مرتبط (۱۰ تا ۲۵ هشتگ)",
  "image_prompts": ["پرامپت انگلیسی تصویر ۱ برای DALL-E", "پرامپت ۲", ...],
  "blog_cover_prompt": "پرامپت انگلیسی برای تصویر کاور بلاگ"
}}

تعداد image_prompts باید دقیقاً {image_count} عدد باشد.
image_prompts باید به انگلیسی و مناسب برای DALL-E باشند، با استایل: premium charcoal product photography, dark moody industrial aesthetic.
blog_body باید HTML باشد نه markdown."""

    response = await client.chat.completions.create(
        model=settings.TEXT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)
    logger.info("text_pack_generated", topic=topic, blog_title=data.get("blog_title"))
    return data
