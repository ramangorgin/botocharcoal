# Botocharcoal Deployment Guide — Debian 12 with systemd & Nginx

A comprehensive guide to deploy the Botocharcoal FastAPI application on a Debian 12 VPS using systemd services, Nginx reverse proxy, and automatic SSL with Let's Encrypt.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Preparation](#system-preparation)
3. [Database Setup](#database-setup)
4. [Redis Setup](#redis-setup)
5. [Application Setup](#application-setup)
6. [Systemd Services](#systemd-services)
7. [Nginx Configuration](#nginx-configuration)
8. [SSL Certificate](#ssl-certificate)
9. [Firewall Configuration](#firewall-configuration)
10. [Monitoring & Maintenance](#monitoring--maintenance)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **VPS/Server**: Debian 12 with sudo access
- **Domain**: A registered domain pointing to your VPS IP
- **SSH Access**: Ability to connect via SSH
- **Disk Space**: At least 5GB free (varies with media storage)
- **Memory**: Minimum 2GB RAM (4GB recommended for production)

---

## System Preparation

### 1. Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Required System Dependencies

```bash
sudo apt install -y \
  python3.11 \
  python3.11-venv \
  python3.11-dev \
  python3-pip \
  postgresql \
  postgresql-contrib \
  redis-server \
  nginx \
  supervisor \
  curl \
  git \
  build-essential \
  libpq-dev \
  libjpeg-dev \
  libfreetype6-dev \
  libssl-dev \
  libffi-dev \
  wget \
  certbot \
  python3-certbot-nginx
```

### 3. Create Application User

Create a dedicated, non-root user to run the application:

```bash
sudo useradd -m -s /bin/bash botocharcoal
sudo su - botocharcoal
```

All subsequent commands should be run as this user unless specified otherwise.

---

## Database Setup

### 1. PostgreSQL Configuration

Switch to the postgres user and create the database:

```bash
sudo su - postgres
```

Then execute:

```sql
CREATE ROLE botocharcoal WITH LOGIN PASSWORD 'your-secure-password' CREATEDB;
CREATE DATABASE botocharcoal OWNER botocharcoal;
```

Exit the postgres user:

```bash
exit
```

### 2. Verify Connection

Test the connection (as botocharcoal user):

```bash
psql -h localhost -U botocharcoal -d botocharcoal -c "SELECT version();"
```

You should be prompted for the password. If successful, you'll see the PostgreSQL version.

### 3. PostgreSQL Remote Access (Optional)

If your database is on a separate server, edit `/etc/postgresql/15/main/postgresql.conf`:

```bash
listen_addresses = '0.0.0.0'  # Listen on all interfaces
```

And in `/etc/postgresql/15/main/pg_hba.conf`, add:

```
host    all             all             your.vps.ip/32          md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

---

## Redis Setup

### 1. Install and Configure Redis

Redis should already be installed. Enable and start it:

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 2. Configure Redis for Persistence

Edit `/etc/redis/redis.conf`:

```bash
sudo nano /etc/redis/redis.conf
```

Ensure these settings:

```
bind 127.0.0.1     # Only localhost, unless needed remotely
protected-mode yes
port 6379
maxmemory 512mb
maxmemory-policy allkeys-lru
appendonly yes      # Enable AOF persistence
```

Restart Redis:

```bash
sudo systemctl restart redis-server
```

### 3. Test Redis Connection

```bash
redis-cli ping
# Should return: PONG
```

---

## Application Setup

### 1. Clone Repository

As the botocharcoal user:

```bash
cd /home/botocharcoal
git clone https://github.com/yourusername/botocharcoal.git app
cd app
```

### 2. Create Python Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Upgrade pip and Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 4. Create `.env` File

```bash
cp .env.example .env
nano .env
```

Fill in the required environment variables:

```bash
APP_ENV=production
SECRET_KEY=your-secret-key-here-use-`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
BASE_URL=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql+asyncpg://botocharcoal:your-secure-password@localhost:5432/botocharcoal
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-your-openai-key
TEXT_MODEL=gpt-4o
IMAGE_MODEL=dall-e-3
GRAPH_API_VERSION=v20.0
IG_LONG_LIVED_ACCESS_TOKEN=your-instagram-token
IG_BUSINESS_ACCOUNT_ID=your-account-id
MEDIA_ROOT=/home/botocharcoal/app/media
MEDIA_URL=/media/
ADMIN_SESSION_MAX_AGE=86400
```

### 5. Create Media Directory

```bash
mkdir -p /home/botocharcoal/app/media
mkdir -p /home/botocharcoal/app/logs
```

### 6. Run Database Migrations

```bash
cd /home/botocharcoal/app
source venv/bin/activate
alembic upgrade head
```

### 7. Verify Application Starts

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Press `Ctrl+C` to stop. If it starts without errors, the setup is correct.

---

## Systemd Services

Create systemd service files to manage the application and Celery worker.

### 1. FastAPI/Gunicorn Service

Create `/etc/systemd/system/botocharcoal-web.service`:

```bash
sudo tee /etc/systemd/system/botocharcoal-web.service > /dev/null <<EOF
[Unit]
Description=Botocharcoal FastAPI Web Service
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=notify
User=botocharcoal
WorkingDirectory=/home/botocharcoal/app
Environment="PATH=/home/botocharcoal/app/venv/bin"
EnvironmentFile=/home/botocharcoal/app/.env
ExecStart=/home/botocharcoal/app/venv/bin/gunicorn \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 127.0.0.1:8000 \
  --access-logfile /home/botocharcoal/app/logs/access.log \
  --error-logfile /home/botocharcoal/app/logs/error.log \
  --log-level info \
  app.main:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 2. Celery Worker Service

Create `/etc/systemd/system/botocharcoal-worker.service`:

```bash
sudo tee /etc/systemd/system/botocharcoal-worker.service > /dev/null <<EOF
[Unit]
Description=Botocharcoal Celery Worker
After=network.target redis-server.service postgresql.service
Requires=redis-server.service postgresql.service

[Service]
Type=forking
User=botocharcoal
WorkingDirectory=/home/botocharcoal/app
Environment="PATH=/home/botocharcoal/app/venv/bin"
EnvironmentFile=/home/botocharcoal/app/.env
ExecStart=/home/botocharcoal/app/venv/bin/celery -A app.tasks.celery_app.celery_app \
  worker \
  -l INFO \
  --concurrency=2 \
  --logfile=/home/botocharcoal/app/logs/celery-worker.log \
  --pidfile=/var/run/botocharcoal-worker.pid

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 3. Celery Beat Service

Create `/etc/systemd/system/botocharcoal-beat.service`:

```bash
sudo tee /etc/systemd/system/botocharcoal-beat.service > /dev/null <<EOF
[Unit]
Description=Botocharcoal Celery Beat Scheduler
After=network.target redis-server.service postgresql.service
Requires=redis-server.service postgresql.service

[Service]
Type=simple
User=botocharcoal
WorkingDirectory=/home/botocharcoal/app
Environment="PATH=/home/botocharcoal/app/venv/bin"
EnvironmentFile=/home/botocharcoal/app/.env
ExecStart=/home/botocharcoal/app/venv/bin/celery -A app.tasks.celery_app.celery_app \
  beat \
  -l INFO \
  --logfile=/home/botocharcoal/app/logs/celery-beat.log \
  --pidfile=/var/run/botocharcoal-beat.pid

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 4. Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable botocharcoal-web.service
sudo systemctl enable botocharcoal-worker.service
sudo systemctl enable botocharcoal-beat.service

sudo systemctl start botocharcoal-web.service
sudo systemctl start botocharcoal-worker.service
sudo systemctl start botocharcoal-beat.service
```

### 5. Verify Services Are Running

```bash
sudo systemctl status botocharcoal-web.service
sudo systemctl status botocharcoal-worker.service
sudo systemctl status botocharcoal-beat.service
```

Check logs:

```bash
tail -f /home/botocharcoal/app/logs/error.log
tail -f /home/botocharcoal/app/logs/celery-worker.log
```

---

## Nginx Configuration

### 1. Create Nginx Config

Create `/etc/nginx/sites-available/botocharcoal`:

```bash
sudo tee /etc/nginx/sites-available/botocharcoal > /dev/null <<'EOF'
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server block
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (populated by certbot)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL best practices
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Logging
    access_log /var/log/nginx/botocharcoal_access.log;
    error_log /var/log/nginx/botocharcoal_error.log;

    # Client body size
    client_max_body_size 10M;

    # Root for static files (optional, handled by FastAPI)
    root /home/botocharcoal/app;

    # Serve static files directly
    location /static/ {
        alias /home/botocharcoal/app/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Serve media files directly
    location /media/ {
        alias /home/botocharcoal/app/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Proxy all other requests to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        # Timeouts for long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Health check endpoint (optional)
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF
```

Replace `yourdomain.com` with your actual domain.

### 2. Enable Nginx Config

```bash
sudo ln -s /etc/nginx/sites-available/botocharcoal /etc/nginx/sites-enabled/botocharcoal
```

### 3. Remove Default Config (Optional)

```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

### 4. Test Nginx Config

```bash
sudo nginx -t
```

You should see:

```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 5. Start and Enable Nginx

```bash
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## SSL Certificate

### 1. Install Let's Encrypt Certificate

```bash
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com
```

Follow the prompts to agree to terms and enter your email.

### 2. Auto-Renewal

Certbot automatically sets up renewal via cron. Verify:

```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
sudo systemctl status certbot.timer
```

### 3. Test Certificate Renewal

```bash
sudo certbot renew --dry-run
```

---

## Firewall Configuration

### 1. Enable UFW (Uncomplicated Firewall)

```bash
sudo ufw enable
```

### 2. Configure Firewall Rules

```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

### 3. Verify Rules

```bash
sudo ufw status
```

---

## Monitoring & Maintenance

### 1. Check Service Status

```bash
systemctl status botocharcoal-web.service
systemctl status botocharcoal-worker.service
systemctl status botocharcoal-beat.service
```

### 2. View Logs

```bash
# Web application logs
tail -f /home/botocharcoal/app/logs/error.log
tail -f /home/botocharcoal/app/logs/access.log

# Celery worker logs
tail -f /home/botocharcoal/app/logs/celery-worker.log

# Celery beat logs
tail -f /home/botocharcoal/app/logs/celery-beat.log

# Nginx logs
tail -f /var/log/nginx/botocharcoal_access.log
tail -f /var/log/nginx/botocharcoal_error.log
```

### 3. Database Backups

Create a backup script at `/home/botocharcoal/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/botocharcoal/backups"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# PostgreSQL backup
pg_dump -U botocharcoal -h localhost botocharcoal | gzip > "$BACKUP_DIR/botocharcoal_$BACKUP_DATE.sql.gz"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "botocharcoal_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/botocharcoal_$BACKUP_DATE.sql.gz"
```

Make it executable:

```bash
chmod +x /home/botocharcoal/backup.sh
```

Add to crontab:

```bash
crontab -e
```

Add line:

```
0 2 * * * /home/botocharcoal/backup.sh
```

### 4. Monitor Disk Space

```bash
df -h
du -sh /home/botocharcoal/app/media
```

### 5. Update Dependencies

Periodically update packages (weekly or monthly):

```bash
cd /home/botocharcoal/app
source venv/bin/activate
pip list --outdated
pip install --upgrade package-name
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check service logs
sudo journalctl -u botocharcoal-web.service -n 50
sudo journalctl -u botocharcoal-web.service -f  # Follow mode
```

### Database Connection Error

```bash
# Test PostgreSQL connection
psql -h localhost -U botocharcoal -d botocharcoal -c "SELECT 1;"

# Check DATABASE_URL in .env
cat /home/botocharcoal/app/.env | grep DATABASE_URL
```

### Redis Connection Error

```bash
# Test Redis connection
redis-cli ping

# Check REDIS_URL in .env
cat /home/botocharcoal/app/.env | grep REDIS_URL
```

### Nginx Won't Start

```bash
# Check syntax
sudo nginx -t

# Check logs
sudo tail -f /var/log/nginx/error.log
```

### High Memory Usage

```bash
# Check memory usage
free -h
top -b -n 1 | head -20

# Reduce Celery concurrency in service file
# Change: --concurrency=4
# To:     --concurrency=2
sudo systemctl restart botocharcoal-worker.service
```

### Slow Response Time

```bash
# Check Gunicorn workers in service file
# Current: -w 4
# Try:     -w 2 (for smaller servers) or -w 8 (for larger servers)
# Formula: (2 × CPU_cores) + 1

sudo systemctl restart botocharcoal-web.service
```

### Media Files Not Loading

```bash
# Verify media directory exists
ls -la /home/botocharcoal/app/media

# Check Nginx can read files
sudo -u www-data ls -la /home/botocharcoal/app/media

# Check file permissions
sudo chown -R botocharcoal:botocharcoal /home/botocharcoal/app/media
sudo chmod -R 755 /home/botocharcoal/app/media
```

### SSL Certificate Issues

```bash
# Check certificate expiry
sudo certbot certificates

# Renew manually
sudo certbot renew --force-renewal

# Check renewal logs
sudo journalctl -u certbot.timer -n 20
```

---

## Production Checklist

- [ ] Domain configured and DNS pointing to VPS
- [ ] All environment variables in `.env` configured
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] OpenAI API key configured
- [ ] Instagram Graph API credentials configured
- [ ] SSL certificate installed
- [ ] All systemd services running
- [ ] Nginx configured and running
- [ ] Firewall rules configured
- [ ] Backup script created and tested
- [ ] Application accessible via domain
- [ ] Admin login works
- [ ] AI content generation tested
- [ ] Media uploads working
- [ ] Celery tasks running (check admin)

---

## Useful Commands

### Service Management

```bash
# Check all Botocharcoal services
sudo systemctl status botocharcoal-*.service

# Restart all services
sudo systemctl restart botocharcoal-web.service botocharcoal-worker.service botocharcoal-beat.service

# View real-time logs
sudo journalctl -u botocharcoal-web.service -f

# Enable on boot
sudo systemctl enable botocharcoal-web.service
```

### Database Management

```bash
# Connect to database
psql -U botocharcoal -d botocharcoal

# Backup database
pg_dump -U botocharcoal -h localhost botocharcoal > backup.sql

# Restore database
psql -U botocharcoal -d botocharcoal < backup.sql
```

### Application Maintenance

```bash
# Update dependencies
cd /home/botocharcoal/app && source venv/bin/activate && pip install -r requirements.txt

# Run migrations
cd /home/botocharcoal/app && source venv/bin/activate && alembic upgrade head

# Check application logs
tail -f /home/botocharcoal/app/logs/error.log
```

### System Monitoring

```bash
# Check resource usage
htop

# Check disk space
df -h

# Check network connections
netstat -tuln | grep -E ':(80|443|5432|6379|8000)'
```

---

## Support

For issues or questions:
1. Check the logs in `/home/botocharcoal/app/logs/`
2. Review the [Troubleshooting](#troubleshooting) section
3. Consult the project README
4. Check systemd journal: `sudo journalctl -u botocharcoal-web.service`

---

**Last Updated**: 2026-06-07  
**Tested On**: Debian 12, Python 3.11, FastAPI 0.111.0
