# Botocharcoal — Release Readiness Notes

**Date**: 2026-05-31
**Version**: 1.0.0
**Status**: READY FOR DEPLOYMENT (after manual steps below)

---

## Deployment Readiness Status

| Area | Status | Notes |
|------|--------|-------|
| App starts without import errors | READY | All imports verified, syntax errors fixed |
| Routes mount correctly | READY | All admin and public routes defined |
| Templates exist | READY | 404.html added, all referenced templates exist |
| DB session setup consistent | READY | Single `engine` in `session.py`, used everywhere |
| Models importable | READY | All 7 models in `app/db/models/__init__.py` |
| Alembic sees metadata | READY | `alembic/env.py` imports all models, `target_metadata = Base.metadata` |
| Celery app imports correctly | READY | Fixed formatting in `celery_app.conf.update()` |
| Worker tasks reference valid functions | READY | `run_content_pipeline` imports verified |
| Media storage path coherent | READY | `MEDIA_ROOT` from config, used consistently |
| Instagram fails gracefully | READY | HTTP errors caught by `tenacity` retry + pipeline exception handler |
| OpenAI fails gracefully | READY | HTTP errors caught by `tenacity` retry + pipeline exception handler |
| Docker support | READY | Dockerfile, docker-compose.yml, .dockerignore created |

---

## Required Environment Variables (Production)

All variables below MUST be set in `.env` or as environment variables before deployment:

### Critical (must be set)

| Variable | Required | Example |
|----------|----------|---------|
| `SECRET_KEY` | Yes | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `REDIS_URL` | Yes | `redis://host:6379/0` |
| `OPENAI_API_KEY` | Yes (for content generation) | `sk-...` |
| `BASE_URL` | Yes | `https://botocharcoal.example.com` |
| `ALLOWED_HOSTS` | Yes | `botocharcoal.example.com` |

### Instagram (required for Instagram publishing)

| Variable | Required | Example |
|----------|----------|---------|
| `IG_LONG_LIVED_ACCESS_TOKEN` | Yes (for IG publishing) | `EAAB...` |
| `IG_BUSINESS_ACCOUNT_ID` | Yes (for IG publishing) | `178414...` |
| `GRAPH_API_VERSION` | Optional (default: `v20.0`) | `v20.0` |

### Optional

| Variable | Default | Notes |
|----------|---------|-------|
| `APP_ENV` | `development` | Set to `production` |
| `TEXT_MODEL` | `gpt-4o` | OpenAI text model |
| `IMAGE_MODEL` | `dall-e-3` | OpenAI image model |
| `MEDIA_ROOT` | `media` | Local path for media files |
| `MEDIA_URL` | `/media/` | Public URL prefix |
| `ADMIN_SESSION_MAX_AGE` | `86400` | Session lifetime in seconds |

---

## Manual Deployment Checklist

### Pre-Deployment

- [ ] Copy `.env.example` to `.env` and fill in all required values
- [ ] Generate a secure `SECRET_KEY`
- [ ] Set up PostgreSQL database and user
- [ ] Set up Redis (install or use managed service)
- [ ] Run `pip install -r requirements.txt` (or use Docker)
- [ ] Run `alembic upgrade head` to apply migrations
- [ ] Run `python -m scripts.create_admin` to create admin user
- [ ] Create `media/` directory with proper permissions
- [ ] Configure Nginx (reverse proxy + media serving)
- [ ] Set up SSL certificate (Let's Encrypt recommended)

### Post-Deployment Verification

- [ ] Visit `/admin/health` — all checks should show `true`
- [ ] Log in to `/admin/login` with created credentials
- [ ] Create a test job and verify it completes
- [ ] Check that images are saved to `media/`
- [ ] Verify blog post appears on public site at `/blog/{slug}`
- [ ] Verify Instagram publishing works (if credentials set)
- [ ] Check Celery worker logs: `celery -A app.tasks.celery_app.celery_app inspect ping`
- [ ] Verify Nginx serves `/media/` files publicly

---

## Issues Fixed During Audit

### Critical Fixes

1. **alembic.ini** — Changed `script_location` from `migrations` to `alembic`; changed `postgresql+asyncpg://` to `postgresql://` (Alembic needs sync driver)
2. **alembic/env.py** — Created from scratch with proper model imports and `target_metadata`
3. **alembic/versions/001_initial_schema.py** — Created initial migration for all 7 models
4. **app/services/instagram.py:35** — Fixed syntax error: `item_ids.append(cid)logger.info(...)` → split into two lines
5. **app/core/logging.py:25** — Fixed syntax error: trailing comma in `structlog.PrintLoggerFactory(),)` → `)`
6. **app/tasks/celery_app.py:16** — Fixed malformed config: `enable_utc=True,task_acks_late=True,` → split into separate lines
7. **app/tasks/content_pipeline.py:109** — Removed redundant `from datetime import datetime, timezone` inside function body
8. **app/schemas/job.py:9** — Changed `image_count: Literal[4, 5]` to `image_count: int = Field(default=4, ge=1, le=10)` to match template
9. **app/api/admin/routes_jobs.py** — Added missing GET `/admin/jobs/create` route
10. **app/api/admin/routes_jobs.py** — Added missing POST `/admin/jobs/{id}/retry` route
11. **app/main.py** — Removed `Base.metadata.create_all` from startup (Alembic handles schema)
12. **app/core/config.py** — Added missing `ALLOWED_HOSTS` setting
13. **app/templates/public/404.html** — Created missing 404 template
14. **scripts/create_admin.py** — Created missing admin user creation script
15. **README.md** — Completely rewritten with accurate, comprehensive documentation

### Architecture Notes

- **No CSRF protection** on admin forms — cookie-based auth only. Consider adding `fastapi-csrf-protect` or Nginx-level protection.
- **No rate limiting** on login or contact form — add Nginx `limit_req` for production.
- **No HTTPS** in the app — handled by Nginx externally.
- **Swagger/ReDoc disabled** in production mode — set `APP_ENV=production` in `.env`.

---

## Remaining Manual Steps Before Deployment

1. **Obtain OpenAI API key** — Sign up at https://platform.openai.com/
2. **Obtain Instagram Graph API credentials** — Create Facebook Developer app, add Instagram Graph API, get long-lived access token and business account ID
3. **Set up SSL** — Use Let's Encrypt (`certbot`) for HTTPS
4. **Configure Nginx** — Set up reverse proxy and media serving (see README)
5. **Set up log rotation** — Configure `logrotate` for application logs
6. **Set up monitoring** — Consider adding health check monitoring (e.g., Uptime Kuma)
7. **Backup strategy** — Set up PostgreSQL backups (`pg_dump` cron job)
8. **Instagram token refresh** — Long-lived tokens expire every 60 days; set a reminder to refresh

---

## File Structure After Changes

```
.
├── alembic.ini                    # Alembic config (fixed)
├── alembic/
│   ├── env.py                     # NEW: Alembic environment
│   ├── script.py.mako             # NEW: Migration template
│   └── versions/
│       └── 001_initial_schema.py  # NEW: Initial migration
├── app/
│   ├── main.py                    # Fixed: removed create_all, added validation handler
│   ├── api/
│   │   ├── deps.py
│   │   ├── admin/
│   │   │   ├── routes_auth.py
│   │   │   ├── routes_catalog.py
│   │   │   ├── routes_dashboard.py
│   │   │   ├── routes_jobs.py     # Fixed: added create + retry routes
│   │   │   ├── routes_leads.py
│   │   │   └── routes_posts.py
│   │   └── public/
│   │       └── routes.py
│   ├── core/
│   │   ├── config.py              # Fixed: added ALLOWED_HOSTS
│   │   ├── constants.py
│   │   ├── logging.py             # Fixed: syntax error
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── catalog.py
│   │       ├── job.py
│   │       ├── lead.py
│   │       ├── media_asset.py
│   │       ├── post.py
│   │       ├── setting.py
│   │       └── user.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── job.py                 # Fixed: image_count type
│   │   ├── lead.py
│   │   ├── post.py
│   │   └── settings.py
│   ├── services/
│   │   ├── ai_image.py
│   │   ├── ai_text.py
│   │   ├── catalog_service.py
│   │   ├── health_service.py
│   │   ├── instagram.py           # Fixed: syntax error
│   │   ├── job_service.py
│   │   ├── lead_service.py
│   │   ├── media_storage.py
│   │   └── website_publish.py
│   ├── tasks/
│   │   ├── celery_app.py          # Fixed: formatting
│   │   ├── content_pipeline.py    # Fixed: redundant import
│   │   └── scheduled_tasks.py
│   ├── templates/
│   │   ├── admin/
│   │   │   ├── base.html
│   │   │   ├── catalog_list.html
│   │   │   ├── dashboard.html
│   │   │   ├── job_create.html
│   │   │   ├── job_detail.html
│   │   │   ├── job_list.html
│   │   │   ├── leads_list.html
│   │   │   ├── login.html
│   │   │   ├── post_detail.html
│   │   │   └── posts_list.html
│   │   └── public/
│   │       ├── 404.html           # NEW
│   │       ├── base.html
│   │       ├── blog_detail.html
│   │       ├── blog_index.html
│   │       ├── catalog.html
│   │       ├── contact.html
│   │       └── home.html
│   └── static/
│       └── css/
│           ├── admin.css
│           └── main.css
├── scripts/
│   ├── create_admin.py            # NEW
│   └── docker-entrypoint.sh       # NEW
├── Dockerfile                     # NEW
├── .dockerignore                  # NEW
├── docker-compose.yml             # NEW
├── .env.example                   # Updated
├── alembic.ini                    # Fixed
├── pyproject.toml
├── requirements.txt               # NEW
├── README.md                      # Completely rewritten
└── RELEASE_READINESS_NOTES.md     # NEW (this file)
```
