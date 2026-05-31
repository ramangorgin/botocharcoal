# Botocharcoal — Persian Charcoal Business Marketing Platform

Marketing website + admin dashboard + AI-assisted content generation + Instagram carousel publishing for a charcoal business.

## Architecture Summary

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Nginx     │────▶│  FastAPI     │────▶│  PostgreSQL  │
│  (reverse   │     │  (Gunicorn)  │     │  (Postgres 16) │
│   proxy)    │     │              │     │              │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐     ┌──────────────┐
                    │  Celery      │────▶│    Redis     │
                    │  Worker      │     │  (Broker)    │
                    └──────────────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  Celery      │
                    │  Beat        │────▶ (scheduled tasks)
                    └──────────────┘
```

## Stack

| Layer        | Technology                                      |
|--------------|-------------------------------------------------|
| Web Framework| FastAPI (Python 3.12+)                          |
| Server       | Gunicorn + Uvicorn workers                      |
| ORM          | SQLAlchemy 2.0 (async)                          |
| Migrations   | Alembic 1.13                                    |
| Database     | PostgreSQL 16                                   |
| Broker       | Redis 7                                         |
| Task Queue   | Celery 5.4                                      |
| Templates    | Jinja2                                          |
| AI Text      | OpenAI API (GPT-4o)                             |
| AI Images    | OpenAI API (DALL·E 3)                           |
| Instagram    | Instagram Graph API (official carousel publishing) |
| Storage      | Local filesystem (`media/`) served via Nginx    |

---

## Features

- **Public Persian RTL website** — home, blog index, blog detail, catalog, contact/lead form
- **Admin dashboard** — login, jobs list/create/detail, posts list/detail, leads inbox, catalog management
- **AI content generation** — topic → Persian caption, hashtags, blog title/body, 4–5 Instagram images, 1 blog cover
- **Instagram publishing** — official Graph API carousel upload (no unofficial automation)
- **Lead capture** — contact form stores leads in PostgreSQL, visible in admin
- **Catalog management** — upload PDF catalogs, serve to public

---

## Prerequisites

- **Linux**: Debian 13 (recommended) or any modern Linux
- **Python**: 3.12+
- **PostgreSQL**: 14+ (tested with 16)
- **Redis**: 6+ (tested with 7)
- **Nginx**: for reverse proxy and media serving (production)
- **OpenAI API key** (for text and image generation)
- **Instagram Graph API** credentials (for publishing)

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `APP_ENV` | `development` or `production` | `production` |
| `SECRET_KEY` | Random secure string for session signing | (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`) |
| `BASE_URL` | Public URL of the application | `https://botocharcoal.example.com` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `botocharcoal.example.com` |
| `DATABASE_URL` | PostgreSQL async connection URL | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `REDIS_URL` | Redis connection URL | `redis://host:6379/0` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `TEXT_MODEL` | OpenAI text model | `gpt-4o` |
| `IMAGE_MODEL` | OpenAI image model | `dall-e-3` |
| `GRAPH_API_VERSION` | Instagram Graph API version | `v20.0` |
| `IG_LONG_LIVED_ACCESS_TOKEN` | Instagram long-lived access token | `EAAB...` |
| `IG_BUSINESS_ACCOUNT_ID` | Instagram business account ID | `178414...` |
| `MEDIA_ROOT` | Local path for media storage | `/home/user/botocharcoal/media` |
| `MEDIA_URL` | Public URL prefix for media | `/media/` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_SESSION_MAX_AGE` | Admin session lifetime in seconds | `86400` |
| `CELERY_MAX_RETRIES` | Max retry count for failed jobs | `3` |

---

## Local Development Setup

### 1. Create virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

### 2. Start PostgreSQL and Redis

```bash
# Debian/Ubuntu
sudo systemctl enable --now postgresql redis-server
```

### 3. Create database and user

```bash
sudo -u postgres psql

SQL:
CREATE DATABASE botocharcoal;
CREATE USER botocharcoal WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE botocharcoal TO botocharcoal;
\q
```

### 4. Run Alembic migrations

```bash
# Ensure .env has correct DATABASE_URL
alembic upgrade head
```

### 5. Create admin user

```bash
python -m scripts.create_admin
# Or with custom credentials:
ADMIN_USERNAME=myadmin ADMIN_PASSWORD=MySecurePass python -m scripts.create_admin
```

### 6. Run FastAPI

```bash
# Development (with auto-reload):
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Production:
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 7. Run Celery Worker

In a separate terminal:

```bash
celery -A app.tasks.celery_app.celery_app worker -l INFO
```

### 8. Run Celery Beat (scheduled tasks)

In another terminal:

```bash
celery -A app.tasks.celery_app.celery_app beat -l INFO
```

---

## Docker Setup

### Prerequisites

- Docker 24+
- Docker Compose v2

### Quick Start

```bash
# 1. Copy environment
cp .env.example .env
# Edit .env with your values

# 2. Start all services
docker compose up -d

# 3. Run migrations (first time only)
docker compose exec web alembic upgrade head

# 4. Create admin user
docker compose exec web python -m scripts.create_admin
```

### Services

| Service | Description | Port |
|---------|-------------|------|
| `web` | FastAPI + Gunicorn | 8000 |
| `postgres` | PostgreSQL database | 5432 |
| `redis` | Redis broker | 6379 |
| `worker` | Celery worker | — |
| `beat` | Celery Beat scheduler | — |

### Volume Persistence

- `postgres_data` — PostgreSQL data
- `redis_data` — Redis data
- `media_data` — Generated images and catalog files

### Stop and Clean Up

```bash
docker compose down
docker compose down -v   # also remove volumes
```

---

## Media / Public URL for Instagram Graph API

Instagram Graph API requires **publicly accessible URLs** for images being uploaded. The application serves media files via:

- **Nginx**: `location /media/ { alias /path/to/media/; }`
- **FastAPI**: `app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT))`

Ensure `BASE_URL` in `.env` matches the public URL so generated `public_url` values in `MediaAsset` records are reachable by Instagram's servers.

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name botocharcoal.example.com;

    location /media/ {
        alias /home/deploy/botocharcoal/media/;
        expires 30d;
    }

    location /static/ {
        alias /home/deploy/botocharcoal/app/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Deployment on Debian 13 (Production)

### 1. System setup

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3-pip \
    postgresql redis-server nginx curl
sudo systemctl enable --now postgresql redis-server nginx
```

### 2. Database setup

```bash
sudo -u postgres psql
CREATE DATABASE botocharcoal;
CREATE USER botocharcoal WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE botocharcoal TO botocharcoal;
\q
```

### 3. Application deployment

```bash
cd /opt
sudo mkdir -p botocharcoal
sudo chown $USER:$USER botocharcoal
cd botocharcoal

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with production values
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Create admin user

```bash
python -m scripts.create_admin
```

### 6. Systemd services

**`/etc/systemd/system/botocharcoal-web.service`**:

```ini
[Unit]
Description=Botocharcoal Web App
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/botocharcoal
Environment="PATH=/opt/botocharcoal/.venv/bin"
ExecStart=/opt/botocharcoal/.venv/bin/gunicorn app.main:app \
    -w 4 -k uvicorn.workers.UvicornWorker \
    -b 127.0.0.1:8000 \
    --access-logfile - \
    --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/botocharcoal-worker.service`**:

```ini
[Unit]
Description=Botocharcoal Celery Worker
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/botocharcoal
Environment="PATH=/opt/botocharcoal/.venv/bin"
ExecStart=/opt/botocharcoal/.venv/bin/celery -A app.tasks.celery_app.celery_app \
    worker -l INFO --concurrency=4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/botocharcoal-beat.service`**:

```ini
[Unit]
Description=Botocharcoal Celery Beat
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/botocharcoal
Environment="PATH=/opt/botocharcoal/.venv/bin"
ExecStart=/opt/botocharcoal/.venv/bin/celery -A app.tasks.celery_app.celery_app \
    beat -l INFO
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now botocharcoal-web botocharcoal-worker botocharcoal-beat
sudo systemctl status botocharcoal-web botocharcoal-worker botocharcoal-beat
```

---

## Alembic Migrations

### Create a new migration (after model changes)

```bash
alembic revision --autogenerate -m "description of changes"
```

### Apply migrations

```bash
alembic upgrade head
```

### Rollback one migration

```bash
alembic downgrade -1
```

### Check current version

```bash
alembic current
```

> **Note**: Alembic uses `psycopg2` (sync driver) for migrations. The app itself uses `asyncpg` (async driver). Ensure both are installed.

---

## API Endpoints

### Public

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home page |
| GET | `/blog` | Blog index |
| GET | `/blog/{slug}` | Blog detail |
| GET | `/catalog` | Catalog page |
| GET | `/contact` | Contact form |
| POST | `/contact` | Submit lead |

### Admin (requires login)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/login` | Login page |
| POST | `/admin/login` | Login action |
| GET | `/admin/logout` | Logout |
| GET | `/admin/dashboard` | Dashboard |
| GET | `/admin/jobs` | Jobs list |
| GET | `/admin/jobs/create` | Create job form |
| POST | `/admin/jobs/create` | Create job |
| GET | `/admin/jobs/{id}` | Job detail |
| POST | `/admin/jobs/{id}/retry` | Retry failed job |
| GET | `/admin/posts` | Posts list |
| GET | `/admin/posts/{id}` | Post detail |
| POST | `/admin/posts/{id}/publish` | Publish to website |
| POST | `/admin/posts/{id}/unpublish` | Unpublish |
| GET | `/admin/leads` | Leads list |
| POST | `/admin/leads/{id}/contacted` | Mark as contacted |
| GET | `/admin/catalog` | Catalog list |
| POST | `/admin/catalog/upload` | Upload catalog |
| GET | `/admin/health` | Health check (JSON) |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Instagram publish fails | Verify `BASE_URL` produces publicly reachable URLs. Check Nginx serves `/media/` correctly. Ensure Instagram access token is valid. |
| Alembic autogenerate shows empty | Ensure all models are imported in `alembic/env.py` and `target_metadata` references `Base.metadata`. |
| DB connection errors | Check `DATABASE_URL` format and PostgreSQL is running. |
| Redis errors | Check `REDIS_URL` and Redis service status. |
| Import errors | Ensure you're in the virtual environment and `pip install -r requirements.txt` completed. |
| Celery tasks not running | Verify worker is running, Redis is reachable, and task modules are listed in `include` in `celery_app.py`. |
| Media files not accessible | Ensure Nginx `alias` path matches `MEDIA_ROOT` and file permissions allow the web server to read them. |

---

## Limitations and Known Assumptions

1. **No containerized Nginx** — Nginx is not included in `docker-compose.yml`. It should be deployed separately on the host for production media serving.
2. **No CSRF protection** — Admin forms use cookie-based sessions without CSRF tokens. For production behind Nginx, consider adding CSRF middleware.
3. **No rate limiting** — The contact form and login have no rate limiting. Add Nginx-level rate limiting for production.
4. **No HTTPS** — HTTPS termination should be handled by Nginx (or a reverse proxy like Traefik).
5. **Instagram token management** — Long-lived tokens must be refreshed manually every 60 days. No automatic refresh is implemented.
6. **Single-writer media** — Media files are stored on the local filesystem. In a multi-instance deployment, use S3-compatible storage.
7. **No API documentation** — Swagger/ReDoc are disabled in production mode (`docs_url=None`). Enable for debugging if needed.
