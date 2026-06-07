# Quick Reference — Botocharcoal Debian 12 Deployment

## Files Provided

| File | Purpose |
|------|---------|
| `PYTHON311_OPTIMIZATION.md` | Summary of Python 3.11 optimization changes |
| `DEPLOYMENT_DEBIAN12.md` | **Complete deployment guide** (main reference) |
| `ENV_TEMPLATE.md` | Environment variable configuration template |
| `pyproject.toml` | **MODIFIED** — Python requirement: `>=3.11` |
| `Dockerfile` | **MODIFIED** — Base image: `python:3.11-slim` |

## Python 3.11 Changes Summary

✅ `pyproject.toml` — Changed `requires-python = ">=3.12"` to `>=3.11`  
✅ `Dockerfile` — Changed `FROM python:3.12-slim` to `python:3.11-slim`  
✅ All dependencies are 3.11 compatible  

---

## Deployment Quick Start

### 1. Prepare VPS (Debian 12)

```bash
# SSH to your VPS
ssh root@your.vps.ip

# Run these commands
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip \
  postgresql postgresql-contrib redis-server nginx supervisor curl git \
  build-essential libpq-dev libjpeg-dev libfreetype6-dev libssl-dev \
  certbot python3-certbot-nginx

# Create app user
sudo useradd -m -s /bin/bash botocharcoal
sudo su - botocharcoal
```

### 2. Clone & Setup Application

```bash
# Still as botocharcoal user
cd /home/botocharcoal
git clone https://github.com/YOUR_REPO/botocharcoal.git app
cd app

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy environment template
cp ENV_TEMPLATE.md .env
nano .env

# Fill in all variables:
# - DATABASE_URL: postgresql+asyncpg://botocharcoal:PASSWORD@localhost:5432/botocharcoal
# - SECRET_KEY: (generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))")
# - OPENAI_API_KEY, IG_LONG_LIVED_ACCESS_TOKEN, etc.

chmod 600 .env
```

### 4. Setup Database

```bash
# Create database (as postgres user via sudo)
sudo su - postgres
psql -c "CREATE ROLE botocharcoal WITH LOGIN PASSWORD 'your-secure-password' CREATEDB;"
psql -c "CREATE DATABASE botocharcoal OWNER botocharcoal;"
exit

# Run migrations (as botocharcoal user)
cd /home/botocharcoal/app && source venv/bin/activate
alembic upgrade head
```

### 5. Create Systemd Services

Copy these service files from `DEPLOYMENT_DEBIAN12.md`:
- `botocharcoal-web.service` → `/etc/systemd/system/`
- `botocharcoal-worker.service` → `/etc/systemd/system/`
- `botocharcoal-beat.service` → `/etc/systemd/system/`

```bash
sudo systemctl daemon-reload
sudo systemctl enable botocharcoal-web.service botocharcoal-worker.service botocharcoal-beat.service
sudo systemctl start botocharcoal-web.service botocharcoal-worker.service botocharcoal-beat.service
```

### 6. Configure Nginx

Copy the Nginx config from `DEPLOYMENT_DEBIAN12.md` to `/etc/nginx/sites-available/botocharcoal`

Replace `yourdomain.com` with your actual domain.

```bash
sudo ln -s /etc/nginx/sites-available/botocharcoal /etc/nginx/sites-enabled/botocharcoal
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Install SSL Certificate

```bash
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com
```

### 8. Setup Firewall

```bash
sudo ufw enable
sudo ufw allow 22/tcp 80/tcp 443/tcp
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

### 9. Verify Deployment

```bash
# Check services
sudo systemctl status botocharcoal-web.service
sudo systemctl status botocharcoal-worker.service
sudo systemctl status botocharcoal-beat.service

# Check logs
tail -f /home/botocharcoal/app/logs/error.log

# Test in browser
curl https://yourdomain.com
```

---

## Directory Structure After Deployment

```
/home/botocharcoal/
├── app/                              # Application code
│   ├── app/                         # Python package
│   ├── alembic/                     # Database migrations
│   ├── media/                       # User uploads
│   ├── logs/                        # Application logs
│   ├── venv/                        # Python environment
│   ├── .env                         # Configuration (SECRET!)
│   └── requirements.txt
└── backups/                         # Database backups

/etc/systemd/system/
├── botocharcoal-web.service        # FastAPI + Gunicorn
├── botocharcoal-worker.service     # Celery worker
└── botocharcoal-beat.service       # Celery scheduler
```

---

## Essential Commands

### Service Management

```bash
sudo systemctl status botocharcoal-*.service          # Check all services
sudo systemctl restart botocharcoal-web.service       # Restart web service
sudo systemctl restart botocharcoal-worker.service    # Restart worker
sudo systemctl logs -u botocharcoal-web.service -f    # View logs (real-time)
```

### View Logs

```bash
tail -f /home/botocharcoal/app/logs/error.log         # Application errors
tail -f /home/botocharcoal/app/logs/celery-worker.log # Celery worker
tail -f /var/log/nginx/botocharcoal_error.log         # Nginx errors
```

### Database Operations

```bash
psql -U botocharcoal -d botocharcoal                  # Connect to DB
pg_dump -U botocharcoal botocharcoal > backup.sql     # Backup
psql -U botocharcoal -d botocharcoal < backup.sql     # Restore
```

### Application Updates

```bash
cd /home/botocharcoal/app
source venv/bin/activate
pip install -r requirements.txt                       # Update deps
alembic upgrade head                                  # Update DB schema
sudo systemctl restart botocharcoal-web.service       # Restart app
```

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Service won't start | Check logs: `sudo journalctl -u botocharcoal-web.service -n 50` |
| Database connection error | Verify `.env` DATABASE_URL and PostgreSQL is running |
| Redis connection error | Verify Redis is running: `redis-cli ping` |
| Nginx 502 error | Check Gunicorn is running: `sudo systemctl status botocharcoal-web.service` |
| SSL certificate error | Check expiry: `sudo certbot certificates` |
| High memory usage | Reduce Celery concurrency in worker service (change `--concurrency=2`) |
| Slow response time | Increase Gunicorn workers (formula: 2×CPU_cores + 1) |

---

## Performance Tuning

### For 2GB RAM Server

In `/etc/systemd/system/botocharcoal-web.service`:
```
-w 2                    # Reduce workers
```

In `/etc/systemd/system/botocharcoal-worker.service`:
```
--concurrency=1         # Reduce concurrency
```

### For 4GB+ RAM Server

In `/etc/systemd/system/botocharcoal-web.service`:
```
-w 8                    # Increase workers
```

In `/etc/systemd/system/botocharcoal-worker.service`:
```
--concurrency=4         # Increase concurrency
```

---

## Production Checklist

- [ ] Domain configured and DNS pointing to VPS IP
- [ ] All `.env` variables filled in correctly
- [ ] Database migrations completed (`alembic upgrade head`)
- [ ] OpenAI API key configured
- [ ] Instagram credentials configured
- [ ] SSL certificate installed
- [ ] All systemd services running
- [ ] Nginx configured and running
- [ ] Firewall configured
- [ ] Backup script created
- [ ] Application accessible via HTTPS
- [ ] Admin login works
- [ ] AI features tested
- [ ] Celery tasks working

---

## Support Resources

1. **Full Guide**: Read [DEPLOYMENT_DEBIAN12.md](DEPLOYMENT_DEBIAN12.md) for detailed instructions
2. **Environment Setup**: See [ENV_TEMPLATE.md](ENV_TEMPLATE.md) for configuration
3. **Python Changes**: Check [PYTHON311_OPTIMIZATION.md](PYTHON311_OPTIMIZATION.md)
4. **Logs Location**: `/home/botocharcoal/app/logs/`
5. **Troubleshooting**: Section in [DEPLOYMENT_DEBIAN12.md](DEPLOYMENT_DEBIAN12.md#troubleshooting)

---

**Last Updated**: 2026-06-07  
**Tested On**: Debian 12, Python 3.11, FastAPI 0.111.0
