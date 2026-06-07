# Git Post-Receive Hook & VPS Initial Deployment Guide

A complete guide to set up automated deployment on your Debian 12 VPS with Git post-receive hooks, systemd services, and continuous sync from your local repository.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [VPS Initial Setup](#vps-initial-setup)
5. [Setting Up Bare Git Repository](#setting-up-bare-git-repository)
6. [Installing Post-Receive Hook](#installing-post-receive-hook)
7. [Creating Systemd Services](#creating-systemd-services)
8. [Testing the Deployment](#testing-the-deployment)
9. [Ongoing Maintenance](#ongoing-maintenance)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This setup enables:

- **Automatic deployment** when you push to the VPS git repository
- **Database migrations** run automatically after checkout
- **Dependencies updated** on every deploy
- **Services restarted** automatically
- **Comprehensive logging** for debugging
- **Zero-downtime deployments** with systemd socket activation

### Deployment Flow

```
Local Machine
    ↓ (git push)
VPS Bare Repository (/root/botocharcoal.ir.git)
    ↓ (post-receive hook triggered)
Working Directory (/var/www/botocharcoal.ir)
    ↓ (migrations, dependency install, service restart)
Live Application
```

---

## Architecture

### Directory Structure on VPS

```
/root/botocharcoal.ir.git/          # Bare git repository (data only)
├── hooks/
│   └── post-receive                 # Deployment hook (this guide)
└── objects/, refs/, HEAD, etc.

/var/www/botocharcoal.ir/            # Working directory (checked out code)
├── app/                             # Application code
├── alembic/                         # Database migrations
├── venv/                            # Python virtual environment
├── logs/                            # Application and deployment logs
├── .env                             # Environment configuration
├── requirements.txt
└── ... (other files)

/etc/systemd/system/
├── botocharcoal-web.service        # FastAPI + Gunicorn service
├── botocharcoal-worker.service     # Celery worker service
└── botocharcoal-beat.service       # Celery beat scheduler
```

---

## Prerequisites

### On Your Local Machine

- Git installed and configured
- Ability to add remote to your git repository
- Access to push to VPS

### On VPS (Debian 12)

- SSH access with sudo privileges
- Domain name pointing to VPS IP (for SSL)
- At least 5GB free disk space
- 2GB+ RAM (4GB recommended)

---

## VPS Initial Setup

### Step 1: Connect to VPS

```bash
ssh root@your-vps-ip
```

### Step 2: Update System

```bash
apt update && apt upgrade -y
```

### Step 3: Install Essential Dependencies

```bash
apt install -y \
  python3.11 \
  python3.11-venv \
  python3.11-dev \
  python3-pip \
  postgresql \
  postgresql-contrib \
  redis-server \
  nginx \
  git \
  build-essential \
  libpq-dev \
  curl \
  wget \
  certbot \
  python3-certbot-nginx
```

### Step 4: Create Application User

```bash
useradd -m -s /bin/bash botocharcoal
usermod -aG sudo botocharcoal
su - botocharcoal
```

### Step 5: Setup PostgreSQL

```bash
sudo su - postgres
```

```sql
CREATE ROLE botocharcoal WITH LOGIN PASSWORD 'your-secure-password' CREATEDB;
CREATE DATABASE botocharcoal OWNER botocharcoal;
\q
```

```bash
exit
```

### Step 6: Start Redis and PostgreSQL

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### Step 7: Verify Connections

```bash
# Test PostgreSQL
psql -h localhost -U botocharcoal -d botocharcoal -c "SELECT version();"

# Test Redis
redis-cli ping
# Should return: PONG
```

---

## Setting Up Bare Git Repository

### Step 1: Create Bare Repository Directory (as root)

```bash
sudo mkdir -p /root/botocharcoal.ir.git
cd /root/botocharcoal.ir.git
sudo git init --bare
```

### Step 2: Create Working Directory

```bash
sudo mkdir -p /var/www/botocharcoal.ir
sudo chown botocharcoal:botocharcoal /var/www/botocharcoal.ir
sudo chmod 755 /var/www/botocharcoal.ir
```

### Step 3: Set Git Config in Bare Repository

```bash
sudo bash -c 'cat > /root/botocharcoal.ir.git/config << EOF
[core]
    bare = true
    repositoryformatversion = 0
[receive]
    denyCurrentBranch = ignore
EOF'
```

### Step 4: Add Remote to Local Repository (on your local machine)

```bash
# In your local botocharcoal directory
cd ~/Projects/botocharcoal

# Add VPS remote
git remote add vps ssh://root@your-vps-ip/root/botocharcoal.ir.git

# Or if using domain:
git remote add vps ssh://root@your-domain.com/root/botocharcoal.ir.git

# Verify remote
git remote -v
```

### Step 5: Push to VPS

```bash
git push vps main
# Or your default branch name
```

---

## Installing Post-Receive Hook

### Step 1: Copy Hook Script to VPS

Option A: Via SCP (from your local machine)

```bash
scp scripts/post-receive-hook.sh root@your-vps-ip:/root/botocharcoal.ir.git/hooks/post-receive
```

Option B: Create directly on VPS

```bash
sudo bash -c 'cat > /root/botocharcoal.ir.git/hooks/post-receive' << 'EOFHOOK'
# [Paste the entire content of scripts/post-receive-hook.sh here]
EOFHOOK
```

### Step 2: Make Hook Executable

```bash
sudo chmod +x /root/botocharcoal.ir.git/hooks/post-receive
```

### Step 3: Verify Hook Ownership

```bash
ls -la /root/botocharcoal.ir.git/hooks/post-receive
```

Should show something like:
```
-rwxr-xr-x 1 root root 8543 Jun  7 20:00 post-receive
```

### Step 4: Allow botocharcoal User to Restart Services

The hook needs to restart systemd services with sudo. Configure passwordless sudo:

```bash
sudo visudo
```

Add this line at the end:

```
botocharcoal ALL=(ALL) NOPASSWD: /bin/systemctl restart botocharcoal-*.service
botocharcoal ALL=(ALL) NOPASSWD: /bin/systemctl is-active
botocharcoal ALL=(ALL) NOPASSWD: /bin/systemctl status
```

---

## Creating Systemd Services

### Service 1: Web Service (FastAPI + Gunicorn)

Create `/etc/systemd/system/botocharcoal-web.service`:

```bash
sudo tee /etc/systemd/system/botocharcoal-web.service > /dev/null <<'EOF'
[Unit]
Description=Botocharcoal FastAPI Web Service
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=notify
User=botocharcoal
WorkingDirectory=/var/www/botocharcoal.ir
Environment="PATH=/var/www/botocharcoal.ir/venv/bin"
EnvironmentFile=/var/www/botocharcoal.ir/.env
ExecStart=/var/www/botocharcoal.ir/venv/bin/gunicorn \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 127.0.0.1:8000 \
  --access-logfile /var/www/botocharcoal.ir/logs/access.log \
  --error-logfile /var/www/botocharcoal.ir/logs/error.log \
  --log-level info \
  app.main:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### Service 2: Celery Worker

Create `/etc/systemd/system/botocharcoal-worker.service`:

```bash
sudo tee /etc/systemd/system/botocharcoal-worker.service > /dev/null <<'EOF'
[Unit]
Description=Botocharcoal Celery Worker
After=network.target redis-server.service postgresql.service
Requires=redis-server.service postgresql.service

[Service]
Type=forking
User=botocharcoal
WorkingDirectory=/var/www/botocharcoal.ir
Environment="PATH=/var/www/botocharcoal.ir/venv/bin"
EnvironmentFile=/var/www/botocharcoal.ir/.env
ExecStart=/var/www/botocharcoal.ir/venv/bin/celery -A app.tasks.celery_app.celery_app \
  worker \
  -l INFO \
  --concurrency=2 \
  --logfile=/var/www/botocharcoal.ir/logs/celery-worker.log \
  --pidfile=/var/run/botocharcoal-worker.pid

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### Service 3: Celery Beat Scheduler

Create `/etc/systemd/system/botocharcoal-beat.service`:

```bash
sudo tee /etc/systemd/system/botocharcoal-beat.service > /dev/null <<'EOF'
[Unit]
Description=Botocharcoal Celery Beat Scheduler
After=network.target redis-server.service postgresql.service
Requires=redis-server.service postgresql.service

[Service]
Type=simple
User=botocharcoal
WorkingDirectory=/var/www/botocharcoal.ir
Environment="PATH=/var/www/botocharcoal.ir/venv/bin"
EnvironmentFile=/var/www/botocharcoal.ir/.env
ExecStart=/var/www/botocharcoal.ir/venv/bin/celery -A app.tasks.celery_app.celery_app \
  beat \
  -l INFO \
  --logfile=/var/www/botocharcoal.ir/logs/celery-beat.log \
  --pidfile=/var/run/botocharcoal-beat.pid

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### Enable Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable botocharcoal-web.service
sudo systemctl enable botocharcoal-worker.service
sudo systemctl enable botocharcoal-beat.service

sudo systemctl start botocharcoal-web.service
sudo systemctl start botocharcoal-worker.service
sudo systemctl start botocharcoal-beat.service
```

### Verify Services

```bash
sudo systemctl status botocharcoal-*.service
```

---

## Testing the Deployment

### Test 1: Manual Trigger

Make a small change locally and push to VPS:

```bash
# On your local machine
echo "# Test deployment" >> README.md
git add README.md
git commit -m "Test deployment"
git push vps main
```

### Test 2: Monitor the Hook

While pushing, watch the VPS logs:

```bash
# On VPS (in another terminal)
tail -f /var/www/botocharcoal.ir/logs/deployment.log
```

### Test 3: Verify Services

After deployment:

```bash
sudo systemctl status botocharcoal-web.service
sudo systemctl status botocharcoal-worker.service
sudo systemctl status botocharcoal-beat.service
```

### Test 4: Check Application

```bash
# Test the application is responding
curl http://127.0.0.1:8000

# Check logs
tail -f /var/www/botocharcoal.ir/logs/error.log
```

---

## Initial Deployment Commands

### First Time Setup

When deploying for the first time or after fresh VPS setup:

```bash
# On VPS as botocharcoal user
cd /var/www/botocharcoal.ir

# 1. Create logs directory
mkdir -p logs

# 2. Copy and configure .env
cp .env.example .env
nano .env  # Edit with your configuration

# 3. Create venv manually if needed
python3.11 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 5. Run migrations
alembic upgrade head

# 6. Test application starts
uvicorn app.main:app --host 127.0.0.1 --port 8000
# Press Ctrl+C to stop

# 7. Start services
sudo systemctl start botocharcoal-web.service
sudo systemctl start botocharcoal-worker.service
sudo systemctl start botocharcoal-beat.service
```

### Verify Initial Setup

```bash
# Check all services running
sudo systemctl status botocharcoal-*.service

# Test database connection
psql -h localhost -U botocharcoal -d botocharcoal -c "SELECT version();"

# Test Redis connection
redis-cli ping

# Check logs
tail -f /var/www/botocharcoal.ir/logs/error.log
```

---

## Ongoing Maintenance

### Daily Operations

```bash
# Check service status
sudo systemctl status botocharcoal-*.service

# View recent logs
tail -30 /var/www/botocharcoal.ir/logs/error.log

# Check deployment logs
tail -30 /var/www/botocharcoal.ir/logs/deployment.log
```

### Regular Deployments

Simply push from local to VPS:

```bash
# Make changes locally
git add .
git commit -m "Your changes"

# Push to VPS
git push vps main

# Monitor deployment
ssh root@your-vps-ip "tail -f /var/www/botocharcoal.ir/logs/deployment.log"
```

### Backup Database

```bash
# Manual backup
pg_dump -U botocharcoal -h localhost botocharcoal | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Automated daily backup (add to crontab)
crontab -e
# Add: 0 2 * * * pg_dump -U botocharcoal -h localhost botocharcoal | gzip > /var/www/botocharcoal.ir/backups/backup_$(date +\%Y\%m\%d).sql.gz
```

### Update Dependencies

```bash
# Update and test locally first
pip install -r requirements.txt --upgrade
# Test locally...
git commit -am "Update dependencies"
git push vps main

# VPS will automatically install new versions via post-receive hook
```

---

## Troubleshooting

### Hook Not Executing

```bash
# Check hook executable
ls -la /root/botocharcoal.ir.git/hooks/post-receive

# Make executable if needed
sudo chmod +x /root/botocharcoal.ir.git/hooks/post-receive

# Check git config
sudo cat /root/botocharcoal.ir.git/config | grep denyCurrentBranch
```

### Services Not Starting After Hook

```bash
# Check service logs
sudo journalctl -u botocharcoal-web.service -n 50
sudo journalctl -u botocharcoal-web.service -f  # Follow mode

# Check deployment log for errors
tail -f /var/www/botocharcoal.ir/logs/deployment.log

# Restart services manually
sudo systemctl restart botocharcoal-web.service
```

### Database Migration Failures

```bash
# Check Alembic version
cd /var/www/botocharcoal.ir
source venv/bin/activate
alembic current

# Show pending migrations
alembic history

# Check migration logs
tail -f /var/www/botocharcoal.ir/logs/deployment.log | grep -i migration

# Manually run migration
alembic upgrade head
```

### Permission Denied on sudo

```bash
# Verify sudoers configuration
sudo cat /etc/sudoers | grep botocharcoal

# If not configured, edit with visudo
sudo visudo
# Add: botocharcoal ALL=(ALL) NOPASSWD: /bin/systemctl restart botocharcoal-*.service
```

### Python Virtual Environment Issues

```bash
# Verify Python version
/var/www/botocharcoal.ir/venv/bin/python --version
# Should show: Python 3.11.x

# Recreate venv if corrupted
rm -rf /var/www/botocharcoal.ir/venv
python3.11 -m venv /var/www/botocharcoal.ir/venv
source /var/www/botocharcoal.ir/venv/bin/activate
pip install -r /var/www/botocharcoal.ir/requirements.txt
```

### Connection Refused on Database/Redis

```bash
# Verify PostgreSQL is running
sudo systemctl status postgresql

# Verify Redis is running
sudo systemctl status redis-server

# Check DATABASE_URL in .env
cat /var/www/botocharcoal.ir/.env | grep DATABASE_URL

# Test connection manually
psql -h localhost -U botocharcoal -d botocharcoal -c "SELECT 1;"
redis-cli ping
```

---

## Performance Tuning

### For 2GB RAM Server

In `/etc/systemd/system/botocharcoal-web.service`, change:
```
ExecStart=... -w 2 ...  # Reduce workers
```

In `/etc/systemd/system/botocharcoal-worker.service`, change:
```
ExecStart=... --concurrency=1 ...  # Reduce concurrency
```

### For 4GB+ RAM Server

In `/etc/systemd/system/botocharcoal-web.service`, change:
```
ExecStart=... -w 8 ...  # Increase workers
```

In `/etc/systemd/system/botocharcoal-worker.service`, change:
```
ExecStart=... --concurrency=4 ...  # Increase concurrency
```

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart botocharcoal-web.service
sudo systemctl restart botocharcoal-worker.service
```

---

## Security Considerations

### Firewall Rules

```bash
# Allow SSH, HTTP, HTTPS only
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### SSH Key-Based Authentication

Instead of password SSH, use key-based auth for better security:

```bash
# On local machine, if not already done
ssh-keygen -t ed25519 -f ~/.ssh/vps_key

# Copy to VPS
ssh-copy-id -i ~/.ssh/vps_key root@your-vps-ip

# Add to ~/.ssh/config for convenience
Host vps-botocharcoal
  HostName your-vps-ip
  User root
  IdentityFile ~/.ssh/vps_key
  IdentitiesOnly yes
```

### SSL Certificate

```bash
# Install Let's Encrypt certificate
sudo certbot certonly --standalone -d your-domain.com

# Auto-renewal is enabled by default
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## Useful Commands Reference

```bash
# ============ Service Management ============

# Check all Botocharcoal services
sudo systemctl status botocharcoal-*.service

# Restart all services
sudo systemctl restart botocharcoal-web.service botocharcoal-worker.service botocharcoal-beat.service

# View real-time service logs
sudo journalctl -u botocharcoal-web.service -f

# Enable services on boot
sudo systemctl enable botocharcoal-*.service

# ============ Database Operations ============

# Connect to database
psql -U botocharcoal -d botocharcoal

# Backup database
pg_dump -U botocharcoal -h localhost botocharcoal > backup.sql

# Restore database
psql -U botocharcoal -d botocharcoal < backup.sql

# ============ Deployment Operations ============

# Trigger manual push to VPS
git push vps main

# Watch deployment logs
tail -f /var/www/botocharcoal.ir/logs/deployment.log

# View error logs
tail -f /var/www/botocharcoal.ir/logs/error.log

# ============ System Monitoring ============

# Check system resource usage
htop

# Disk space usage
df -h

# Memory usage
free -h

# Network connections
netstat -tuln | grep -E ':(80|443|5432|6379|8000)'

# ============ Application Testing ============

# Test API endpoint
curl -v http://your-domain.com/health

# Test database from container
alembic current

# Check Python imports
python3.11 -c "from app.main import app; print('OK')"
```

---

## Summary

With this setup, you now have:

✅ **Automated Git-based deployment** - Push code, it deploys automatically  
✅ **Database migrations** - Alembic runs on every deployment  
✅ **Dependency management** - pip automatically installs new packages  
✅ **Service management** - systemd handles auto-restart and monitoring  
✅ **Comprehensive logging** - Track all deployments and errors  
✅ **Production-ready** - SSL, Nginx, firewall configured  

---

**Last Updated**: 2026-06-07  
**Python Version**: 3.11  
**OS**: Debian 12 (Bookworm)
