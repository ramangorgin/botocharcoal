# app/core/template_filters.py
import re
import jdatetime
from datetime import datetime


def to_persian(value):
    """Convert English numbers to Persian"""
    if value is None:
        return ""
    persian_digits = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
    return str(value).translate(persian_digits)


def clean_hashtags(text):
    """Remove hashtags from caption text"""
    if not text:
        return text

    # Remove lines that only contain hashtags
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        words = line.split()
        if words:
            hashtag_count = sum(1 for w in words if w.startswith('#'))
            if hashtag_count / len(words) > 0.5:
                continue
        cleaned_lines.append(line)

    result = '\n'.join(cleaned_lines)

    # Also remove hashtags from the end of the caption
    result = re.sub(r'(\s*#[^\s]+\s*)+$', '', result)

    return result.strip()


def format_jalali(value):
    """Format datetime to Jalali calendar with Persian digits"""
    if not value:
        return "-"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except:
            return str(value)

    try:
        jalali_date = jdatetime.datetime.fromgregorian(datetime=value)
        persian_months = [
            'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
        ]

        day = to_persian(jalali_date.day)
        month = persian_months[jalali_date.month - 1]
        year = to_persian(jalali_date.year)
        hour = to_persian(f"{jalali_date.hour:02d}")
        minute = to_persian(f"{jalali_date.minute:02d}")

        return f"{day} {month} {year} - {hour}:{minute}"
    except Exception:
        return str(value)
