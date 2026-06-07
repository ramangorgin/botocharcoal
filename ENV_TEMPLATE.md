# Environment Configuration Template for Debian 12 Deployment

This file contains all environment variables needed for production deployment.

## Instructions

1. Copy this template:
   ```bash
   cp ENV_TEMPLATE.md .env
   ```

2. Edit `.env` and replace all placeholder values:
   ```bash
   nano /home/botocharcoal/app/.env
   ```

3. Make sure the file is readable only by the application user:
   ```bash
   chmod 600 /home/botocharcoal/app/.env
   ```

---

## Environment Variables

### Application Settings

```bash
# Application environment
APP_ENV=production

# Secret key for session signing (CHANGE THIS!)
# Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-secret-key-here-minimum-32-characters

# Public base URL of your application
BASE_URL=https://yourdomain.com

# Allowed hostnames (comma-separated)
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Session timeout in seconds (default: 86400 = 24 hours)
ADMIN_SESSION_MAX_AGE=86400
```

### Database Configuration

```bash
# PostgreSQL connection URL
# Format: postgresql+asyncpg://username:password@host:port/database
# For local: postgresql+asyncpg://botocharcoal:your-secure-password@localhost:5432/botocharcoal
DATABASE_URL=postgresql+asyncpg://botocharcoal:your-secure-password@localhost:5432/botocharcoal
```

### Redis Configuration

```bash
# Redis connection URL
# For local: redis://localhost:6379/0
# For remote: redis://username:password@host:port/db
REDIS_URL=redis://localhost:6379/0
```

### OpenAI Configuration

```bash
# OpenAI API key (from https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-your-actual-api-key-here

# Text generation model
TEXT_MODEL=gpt-4o

# Image generation model
IMAGE_MODEL=dall-e-3
```

### Instagram Configuration

```bash
# Instagram Graph API version
GRAPH_API_VERSION=v20.0

# Instagram long-lived access token (from Meta Developer Console)
# Instructions:
# 1. Go to https://developers.facebook.com/
# 2. Create an app
# 3. Add Instagram Graph API product
# 4. Get the long-lived access token
# 5. The token starts with 'EAAB...'
IG_LONG_LIVED_ACCESS_TOKEN=EAAB_YOUR_TOKEN_HERE

# Instagram business account ID
# You can get this from the Instagram Graph API explorer
IG_BUSINESS_ACCOUNT_ID=17841401234567890
```

### Media & File Configuration

```bash
# Local path for media storage
# This should match the volume mount in docker-compose or systemd service
MEDIA_ROOT=/home/botocharcoal/app/media

# Public URL prefix for media files (served via Nginx)
MEDIA_URL=/media/
```

### Celery Configuration

```bash
# Maximum number of task retries
CELERY_MAX_RETRIES=3
```

---

## Security Checklist

- [ ] `SECRET_KEY` is a unique, random string (minimum 32 characters)
- [ ] Database password is strong and unique
- [ ] `APP_ENV` is set to `production`
- [ ] `.env` file permissions are `600` (only owner readable)
- [ ] No `.env` file committed to Git (check `.gitignore`)
- [ ] All sensitive values are filled in
- [ ] `ALLOWED_HOSTS` matches your actual domain(s)
- [ ] HTTPS is enabled (`BASE_URL` starts with `https://`)

---

## Generating Secure Secret Key

Run this command to generate a secure secret key:

```bash
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

Copy the output to your `.env` file.

---

## Development vs Production

### Development (.env)

```bash
APP_ENV=development
BASE_URL=http://localhost:8000
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/botocharcoal_dev
```

### Production (.env)

```bash
APP_ENV=production
BASE_URL=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql+asyncpg://botocharcoal:secure-password@localhost:5432/botocharcoal
```

---

## Verifying Configuration

After setting up `.env`, verify it's correct:

```bash
# Check file exists and has correct permissions
ls -la /home/botocharcoal/app/.env

# Should show: -rw------- 1 botocharcoal botocharcoal
# (only owner can read)

# Test database connection
cd /home/botocharcoal/app
source venv/bin/activate
python -c "from app.db.session import engine; print('DB connection works!')"

# Test Redis connection
python -c "import redis; r = redis.from_url('$REDIS_URL'); print(r.ping())"
```

---

## Instagram API Setup

### Step-by-Step Instagram Configuration

1. **Go to Meta Developer Console**
   - https://developers.facebook.com/

2. **Create an App**
   - Click "My Apps" → "Create App"
   - Choose "Business" type
   - Fill in app details

3. **Add Instagram Graph API**
   - In app dashboard, find "Products"
   - Add "Instagram Graph API"
   - Add "Instagram Basic Display" (if needed)

4. **Create Access Token**
   - Go to Tools & Support → Graph API Explorer
   - Select your app from the dropdown
   - Select "Get User Access Token"
   - Request permissions: `instagram_business_content_publish`, `pages_read_engagement`
   - Generate token

5. **Convert to Long-Lived Token**
   - The initial token expires in 1 hour
   - To get a long-lived token (60 days):
   ```bash
   curl -i -X GET "https://graph.instagram.com/v20.0/access_token?grant_type=ig_refresh_token&access_token=YOUR_SHORT_LIVED_TOKEN"
   ```

6. **Get Business Account ID**
   - Use this API call:
   ```bash
   curl -i -X GET "https://graph.instagram.com/me/instagram_business_account?access_token=YOUR_LONG_LIVED_TOKEN"
   ```
   - Look for `id` in the response

7. **Set in .env**
   ```bash
   IG_LONG_LIVED_ACCESS_TOKEN=EAAB_YOUR_LONG_LIVED_TOKEN
   IG_BUSINESS_ACCOUNT_ID=YOUR_BUSINESS_ACCOUNT_ID
   ```

---

## Troubleshooting Configuration

### "Invalid OPENAI_API_KEY"
- Check that the key starts with `sk-`
- Verify it's not expired or revoked at https://platform.openai.com/api-keys
- Ensure no extra whitespace in `.env`

### "Cannot connect to PostgreSQL"
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Test connection manually: `psql -h localhost -U botocharcoal -d botocharcoal`
- Check database password in DATABASE_URL matches
- Ensure database and user exist

### "Cannot connect to Redis"
- Verify Redis is running: `sudo systemctl status redis-server`
- Test connection: `redis-cli ping` (should return PONG)
- Check REDIS_URL is correct

### "Instagram API errors"
- Verify access token hasn't expired (max 60 days)
- Check business account ID is correct
- Ensure app has required permissions
- Check API version in GRAPH_API_VERSION matches

---

## File Location

After creating `.env` from this template, it should be at:

```
/home/botocharcoal/app/.env
```

**DO NOT commit this file to Git!** It contains sensitive credentials.

---

**Last Updated**: 2026-06-07
