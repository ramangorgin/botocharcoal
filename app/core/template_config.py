# app/core/template_config.py
from pathlib import Path
from fastapi.templating import Jinja2Templates
from app.core.template_filters import to_persian, clean_hashtags, format_jalali

# Create templates instance with custom filters
BASE_DIR = Path(__file__).resolve().parent.parent  # Points to app/
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Register filters
templates.env.filters['to_persian'] = to_persian
templates.env.filters['clean_hashtags'] = clean_hashtags
templates.env.filters['format_jalali'] = format_jalali
