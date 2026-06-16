import asyncio
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# load .env explicitly
load_dotenv(PROJECT_ROOT / ".env")

from app.core.config import settings
from app.db.models.post import Post


def slugify(value: str) -> str:
    """
    تبدیل متن فارسی/انگلیسی به slug ساده و URL-safe.
    """
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    value = re.sub(r"[-\s]+", "-", value, flags=re.UNICODE)
    return value.strip("-")


POSTS = [
    {
        "topic": "لینوکس",
        "title": "راهنمای کامل مدیریت فایل‌ها در لینوکس برای مبتدی‌ها",
        "body_html": """
            <h2>مدیریت فایل‌ها در لینوکس</h2>
            <p>در لینوکس، تقریباً همه چیز فایل است؛ از خود فایل‌های متنی تا دستگاه‌ها و حتی برخی تنظیمات سیستم.</p>
            <h3>دستورهای پایه</h3>
            <ul>
                <li><code>ls</code> برای مشاهده محتویات دایرکتوری</li>
                <li><code>cp</code> برای کپی کردن فایل</li>
                <li><code>mv</code> برای جابه‌جایی یا تغییر نام</li>
                <li><code>rm</code> برای حذف</li>
                <li><code>mkdir</code> برای ساخت پوشه</li>
            </ul>
        """,
        "summary": "مروری عملی بر دستورهای اصلی مدیریت فایل در لینوکس برای کاربران مبتدی.",
        "category": "Linux",
        "poster": "رامان",
        "cover_image_url": "https://example.com/images/linux-files.jpg",
        "instagram_caption": "مدیریت فایل‌ها در لینوکس از پایه تا کاربردی 🚀\n\nاگر تازه وارد لینوکس شدی، این پست برای توئه.",
        "hashtags": "#linux #debian #terminal #cli #sysadmin",
        "website_status": "published",
        "meta_title": "راهنمای مدیریت فایل‌ها در لینوکس",
        "meta_description": "دستورهای پایه و کاربردی مدیریت فایل‌ها در لینوکس برای مبتدی‌ها.",
        "og_title": "مدیریت فایل‌ها در لینوکس",
        "og_description": "با دستورهای اصلی لینوکس برای مدیریت فایل‌ها آشنا شو.",
        "og_image": "https://example.com/images/linux-files-og.jpg",
        "source_type": "seed",
        "blog_enabled": True,
        "instagram_enabled": True,
        "ai_prompt": None,
        "ai_payload": None,
    },
    {
        "topic": "شبکه",
        "title": "پینگ، Traceroute و DNS؛ سه ابزار حیاتی در عیب‌یابی شبکه",
        "body_html": """
            <h2>عیب‌یابی شبکه</h2>
            <p>وقتی یک سرویس در دسترس نیست، اولین سؤال این است: مشکل از DNS است، مسیر شبکه است، یا خود سرویس؟</p>
            <p>با <code>ping</code>، <code>traceroute</code> و <code>dig</code> می‌توانی خیلی سریع لایه‌ی مشکل را پیدا کنی.</p>
        """,
        "summary": "آشنایی با سه ابزار کلیدی برای تشخیص سریع مشکلات شبکه.",
        "category": "Networking",
        "poster": "رامان",
        "cover_image_url": "https://example.com/images/network-troubleshooting.jpg",
        "instagram_caption": "سه ابزار طلایی برای عیب‌یابی شبکه: ping، traceroute و DNS 🔧",
        "hashtags": "#networking #dns #ping #traceroute #linux",
        "website_status": "published",
        "meta_title": "عیب‌یابی شبکه با ping و traceroute",
        "meta_description": "یاد بگیر چطور مشکلات شبکه را با ابزارهای پایه عیب‌یابی کنی.",
        "og_title": "عیب‌یابی شبکه با ابزارهای پایه",
        "og_description": "ping، traceroute و DNS را برای تشخیص سریع مشکل یاد بگیر.",
        "og_image": "https://example.com/images/network-troubleshooting-og.jpg",
        "source_type": "seed",
        "blog_enabled": True,
        "instagram_enabled": True,
        "ai_prompt": None,
        "ai_payload": None,
    },
    {
        "topic": "برنامه‌نویسی",
        "title": "چرا async در پایتون برای کارهای I/O عالی است؟",
        "body_html": """
            <h2>Async در پایتون</h2>
            <p>وقتی کارهای تو بیشتر I/O-bound هستند مثل دیتابیس، شبکه یا API call، async می‌تواند throughput را به‌طور محسوسی بهتر کند.</p>
            <p>اما برای محاسبات CPU-bound، معمولاً async راه‌حل اصلی نیست.</p>
        """,
        "summary": "توضیح ساده و فنی درباره مزیت‌های async در پایتون برای I/O.",
        "category": "Programming",
        "poster": "رامان",
        "cover_image_url": "https://example.com/images/python-async.jpg",
        "instagram_caption": "Async در پایتون یعنی بهره‌وری بیشتر در کارهای I/O ⚡",
        "hashtags": "#python #asyncio #programming #backend #api",
        "website_status": "published",
        "meta_title": "چرا async در پایتون مهم است؟",
        "meta_description": "مزیت‌های async برای عملیات I/O در پایتون را یاد بگیر.",
        "og_title": "مزیت‌های async در پایتون",
        "og_description": "اگر با API، دیتابیس یا شبکه کار می‌کنی، async را بشناس.",
        "og_image": "https://example.com/images/python-async-og.jpg",
        "source_type": "seed",
        "blog_enabled": True,
        "instagram_enabled": True,
        "ai_prompt": None,
        "ai_payload": None,
    },
    {
        "topic": "DevOps",
        "title": "Docker چیست و چرا برای محیط‌های توسعه و production مهم است؟",
        "body_html": """
            <h2>Docker</h2>
            <p>Docker کمک می‌کند وابستگی‌های برنامه را در یک محیط قابل حمل و تکرارپذیر بسته‌بندی کنی.</p>
            <p>این یعنی dev و production بیشتر شبیه هم می‌شوند و خطاهای محیطی کمتر می‌شود.</p>
        """,
        "summary": "مقدمه‌ای کاربردی بر Docker و نقش آن در توسعه و استقرار.",
        "category": "DevOps",
        "poster": "رامان",
        "cover_image_url": "https://example.com/images/docker.jpg",
        "instagram_caption": "Docker یکی از ستون‌های اصلی دنیای DevOps است 🐳",
        "hashtags": "#docker #devops #containers #linux #backend",
        "website_status": "published",
        "meta_title": "Docker چیست؟",
        "meta_description": "با مفهوم Docker و کاربرد آن در dev و production آشنا شو.",
        "og_title": "Docker برای توسعه و production",
        "og_description": "چرا Docker برای محیط‌های توسعه و استقرار مهم است؟",
        "og_image": "https://example.com/images/docker-og.jpg",
        "source_type": "seed",
        "blog_enabled": True,
        "instagram_enabled": True,
        "ai_prompt": None,
        "ai_payload": None,
    },
    {
        "topic": "امنیت",
        "title": "اصول اولیه امنیت لینوکس که هر مدیر سرور باید بداند",
        "body_html": """
            <h2>امنیت پایه در لینوکس</h2>
            <p>امنیت واقعی از تنظیمات ساده شروع می‌شود: یوزر کم‌دسترسی، SSH امن، فایروال، آپدیت منظم و لاگ‌خوانی.</p>
            <p>اگر این پایه‌ها درست نباشند، ابزارهای پیچیده هم معجزه نمی‌کنند.</p>
        """,
        "summary": "مهم‌ترین اصول ابتدایی امنیت در سرورهای لینوکسی.",
        "category": "Security",
        "poster": "رامان",
        "cover_image_url": "https://example.com/images/linux-security.jpg",
        "instagram_caption": "امنیت لینوکس از پایه‌های ساده شروع می‌شود 🔐",
        "hashtags": "#security #linux #server #ssh #hardening",
        "website_status": "published",
        "meta_title": "اصول امنیت لینوکس",
        "meta_description": "با پایه‌های امنیت سرور لینوکسی آشنا شو.",
        "og_title": "امنیت پایه در لینوکس",
        "og_description": "برای هر مدیر سرور، امنیت از همین اصول اولیه شروع می‌شود.",
        "og_image": "https://example.com/images/linux-security-og.jpg",
        "source_type": "seed",
        "blog_enabled": True,
        "instagram_enabled": True,
        "ai_prompt": None,
        "ai_payload": None,
    },
]


async def seed_posts() -> None:
    db_url = settings.DATABASE_URL
    if not db_url:
        raise RuntimeError("DATABASE_URL is empty or not loaded.")

    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with SessionLocal() as db:
            inserted = 0
            skipped = 0

            for item in POSTS:
                slug = slugify(item["title"])

                exists_stmt = text("SELECT id FROM posts WHERE slug = :slug LIMIT 1")
                result = await db.execute(exists_stmt, {"slug": slug})
                existing = result.scalar_one_or_none()

                if existing is not None:
                    print(f"Skipped existing post: {slug}")
                    skipped += 1
                    continue

                post = Post(
                    topic=item["topic"],
                    title=item["title"],
                    slug=slug,
                    body_html=item["body_html"],
                    summary=item["summary"],
                    category=item["category"],
                    poster=item["poster"],
                    cover_image_url=item["cover_image_url"],
                    instagram_caption=item["instagram_caption"],
                    hashtags=item["hashtags"],
                    website_status=item["website_status"],
                    meta_title=item["meta_title"],
                    meta_description=item["meta_description"],
                    og_title=item["og_title"],
                    og_description=item["og_description"],
                    og_image=item["og_image"],
                    source_type=item["source_type"],
                    blog_enabled=item["blog_enabled"],
                    instagram_enabled=item["instagram_enabled"],
                    ai_prompt=item["ai_prompt"],
                    ai_payload=item["ai_payload"],
                )

                db.add(post)
                inserted += 1

            await db.commit()

            print(f"Seed completed. Inserted: {inserted}, Skipped: {skipped}")

    except SQLAlchemyError as exc:
        raise RuntimeError(f"Database error while seeding posts: {exc}") from exc
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_posts())
