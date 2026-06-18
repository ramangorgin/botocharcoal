# Botocharcoal - AI-Powered Content Generation Platform

A FastAPI-based content management system with AI-powered blog and Instagram content generation, designed for Botocharcoal, a premium Persian charcoal brand.

## Tech Stack

- **Backend**: Python 3.13, FastAPI
- **Database**: PostgreSQL 17 with SQLAlchemy 2.0 (async)
- **Task Queue**: Celery with Redis broker
- **AI Integration**: OpenAI-compatible API (GapGPT)
- **Web Server**: Nginx reverse proxy with SSL
- **Deployment**: Git-based auto-deployment with systemd services

## Project Structure

```
botocharcoal/
├── app/
│   ├── api/
│   │   ├── admin/           # Admin panel routes
│   │   ├── public/          # Public-facing routes
│   │   └── router.py        # Main API router
│   ├── core/                # Configuration and utilities
│   ├── db/                  # Database models and session
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   ├── tasks/               # Celery background tasks
│   └── templates/           # Jinja2 templates
├── alembic/                 # Database migrations
├── media/                   # Uploaded and generated media
├── requirements.txt
└── alembic.ini
```

## Database Schema

### Tables

#### `users`
Stores admin users for the admin panel.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| username | VARCHAR(100) | Unique username |
| password_hash | VARCHAR(255) | Bcrypt-hashed password |
| is_admin | BOOLEAN | Admin flag (default: true) |
| created_at | TIMESTAMP | Creation timestamp |

#### `ai_settings`
Configuration for AI model integration (single-row table).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| provider | VARCHAR(50) | Provider name (e.g., "custom") |
| base_url | TEXT | API base URL |
| api_key | TEXT | API authentication key |
| text_model | VARCHAR(100) | Text generation model |
| image_model | VARCHAR(100) | Image generation model |
| system_prompt | TEXT | System prompt for AI |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

#### `jobs`
AI content generation job requests.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| topic | VARCHAR(255) | Content topic |
| blog_text_instructions | TEXT | Instructions for blog text |
| blog_image_instructions | TEXT | Instructions for blog cover image |
| instagram_text_instructions | TEXT | Instructions for Instagram caption |
| instagram_image_instructions | TEXT | Instructions for Instagram images |
| blog_image_count | INTEGER | Number of blog images (default: 1) |
| instagram_image_count | INTEGER | Number of Instagram images (default: 1) |
| auto_publish | BOOLEAN | Auto-publish to blog after generation |
| status | VARCHAR(50) | Job status: pending/processing/completed/failed |
| post_id | INTEGER | FK to posts table |
| error_message | TEXT | Error message if failed |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

#### `posts`
Generated or manually created content.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| topic | VARCHAR(255) | Content topic |
| title | VARCHAR(255) | Post title |
| slug | VARCHAR(255) | URL-friendly slug (unique) |
| body_html | TEXT | Blog post HTML content |
| summary | TEXT | Short summary |
| instagram_caption | TEXT | Instagram caption text |
| hashtags | VARCHAR(500) | Space-separated hashtags |
| website_status | VARCHAR(50) | Blog status: draft/published |
| instagram_status | VARCHAR(50) | Instagram status: draft/ready |
| published_to_website_at | TIMESTAMP | Blog publish timestamp |
| source_type | VARCHAR(50) | Source: ai/manual |
| ai_prompt | TEXT | JSON of AI instructions used |
| ai_payload | JSON | Full AI response data |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

**Relationships:**
- `tags`: Many-to-many via `post_tags`
- `categories`: Many-to-many via `post_categories`
- `media_assets`: One-to-many (cascade delete)

#### `media_assets`
Images associated with posts.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| post_id | INTEGER | FK to posts (CASCADE delete) |
| role | VARCHAR(50) | Image role: blog_cover/instagram_image |
| prompt | TEXT | AI prompt used to generate |
| local_path | TEXT | Local filesystem path |
| public_url | TEXT | Web-accessible URL |
| width | INTEGER | Image width |
| height | INTEGER | Image height |
| sort_order | INTEGER | Display order |
| created_at | TIMESTAMP | Creation timestamp |

#### `tags`
Content tags for posts.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR(100) | Unique tag name |

#### `categories`
Content categories for posts.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR(100) | Unique category name |

#### Association Tables
- `post_tags`: (post_id, tag_id) - Many-to-many
- `post_categories`: (post_id, category_id) - Many-to-many

## Content Generation Pipeline

### 1. Job Creation
1. Admin creates a job via `/admin/jobs/create`
2. Specifies topic and separate instructions for:
   - Blog text content
   - Blog cover image
   - Instagram caption text
   - Instagram post images
3. Sets image counts and auto-publish preference

### 2. Task Processing (Celery)
The `process_job_task` executes the following steps:

**Text Generation (Two separate API calls):**
1. Blog content: Sends topic + blog_text_instructions to AI
   - Returns JSON with: title, slug, body_html, summary
2. Instagram caption: Sends topic + instagram_text_instructions to AI
   - Returns JSON with: instagram_caption, hashtags

**Image Generation:**
3. Blog cover image: Uses blog_image_instructions as prompt
4. Instagram images: Uses instagram_image_instructions as prompt
   - Generates specified count of images
   - Images downloaded from AI provider URL
   - Saved locally to `media/generated_images/`
   - Stored in `media_assets` table with appropriate role

**Post Creation:**
5. Creates a `posts` record with:
   - Blog content (title, slug, body_html, summary)
   - Instagram content (caption, hashtags)
   - Status set to "draft" (or "published" if auto_publish=true)
   - Source type set to "ai"
   - Full AI prompt and payload stored for reference

**Image Storage:**
6. Blog cover: Saved as `media_assets` with role="blog_cover"
7. Instagram images: Saved as `media_assets` with role="instagram_image"

### 3. AI Integration Details

**API Provider:** GapGPT (OpenAI-compatible)
- Base URL: `https://api.gapgpt.app/v1`
- Authentication: API key via Bearer token

**Text Models:** Configurable via admin panel
- Default: gpt-4o
- Fallback chain: gpt-4o → gpt-4o-mini → gpt-4-turbo

**Image Models:** Configurable via admin panel
- Default: gapgpt/z-image
- Fallback chain: gapgpt/z-image → dall-e-3 → gpt-image-1 → dall-e-2

**Rate Limiting Protection:**
- 3-second delay between text generation calls
- 5-second delay between image generation batches
- Exponential backoff on 429 errors (5s, 10s, 20s, 40s, 80s)
- Maximum 5 retry attempts per request

**Image Handling:**
- Images generated by AI are returned as URLs
- System downloads images from AI provider
- Saved locally to `media/generated_images/`
- Database stores web-accessible path
- Nginx serves `/media/` directory directly

## API Routes

### Public Routes
- `GET /` - Homepage with recent published posts
- `GET /blog` - Blog listing page
- `GET /blog/{slug}` - Single blog post
- `GET /about` - About page
- `GET /contact` - Contact page

### Admin Routes
- `GET /admin/login` - Admin login
- `GET /admin/dashboard` - Dashboard with stats
- `GET /admin/posts` - List posts
- `GET /admin/posts/create` - Manual post creation form
- `POST /admin/posts/create` - Create post manually
- `GET /admin/posts/{id}` - View post
- `GET /admin/posts/{id}/edit` - Edit post form
- `POST /admin/posts/{id}/edit` - Update post
- `POST /admin/posts/{id}/publish` - Publish post
- `POST /admin/posts/{id}/unpublish` - Unpublish post
- `POST /admin/posts/{id}/delete` - Delete post
- `GET /admin/jobs` - List jobs
- `GET /admin/jobs/create` - Job creation form
- `POST /admin/jobs` - Create job (triggers AI generation)
- `GET /admin/jobs/{id}` - View job with results
- `POST /admin/jobs/{id}/abort` - Abort running job
- `POST /admin/jobs/{id}/retry` - Retry failed job
- `GET /admin/ai-settings` - AI settings form
- `POST /admin/ai-settings` - Update AI settings

## Deployment

### Server Requirements
- Debian 13
- Python 3.13
- PostgreSQL 17
- Redis
- Nginx

### Services
- `botocharcoal-web.service` - Uvicorn ASGI server (port 8000)
- `botocharcoal-worker.service` - Celery background worker
- `nginx.service` - Reverse proxy (ports 80, 443)

### Auto-Deployment
Git push to `production` remote triggers post-receive hook:
1. Checks out latest code from bare repository
2. Creates/updates Python virtual environment
3. Installs dependencies via Iranian PyPI mirror
4. Runs Alembic database migrations
5. Restarts systemd services
6. Reloads Nginx configuration

### Environment Variables
```
APP_ENV=production
SECRET_KEY=<random-secret-key>
BASE_URL=https://botocharcoal.ir
ALLOWED_HOSTS=botocharcoal.ir,www.botocharcoal.ir
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/botocharcoal
REDIS_URL=redis://localhost:6379/0
MEDIA_ROOT=media
MEDIA_URL=/media/
ADMIN_SESSION_MAX_AGE=86400
CELERY_MAX_RETRIES=3
```

## Development

### Local Setup
```bash
# Clone repository
git clone <repo-url>
cd botocharcoal

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your local settings

# Run migrations
alembic upgrade head

# Start services
# Terminal 1: FastAPI server
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery worker
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2

# Terminal 3: Redis (if not running)
redis-server
```

### Database Migrations
```bash
# Generate migration from model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## License

Proprietary - All rights reserved.
# Production deployed Thu Jun 18 06:56:36 PM +0330 2026
# testing the deploy
