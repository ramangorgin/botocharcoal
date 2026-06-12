import sys
sys.path.insert(0, '/home/raman/Projects/botocharcoal')
from datetime import datetime
import jdatetime

MONTHS_PERSIAN = [
    '', 'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد',
    'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
]
PERSIAN_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')

def to_persian_digits(s):
    return str(s).translate(PERSIAN_DIGITS)

def format_persian_date(dt):
    if not dt:
        return ''
    jalali = jdatetime.datetime.fromgregorian(datetime=dt)
    day = to_persian_digits(jalali.day)
    month = MONTHS_PERSIAN[jalali.month - 1]
    year = to_persian_digits(jalali.year)
    return f'{day} {month} {year}'

# Test with a sample date
test_date = datetime(2026, 6, 12)
result = format_persian_date(test_date)
print(f"Result: {result}")
print(f"Contains Persian digits: {any(c in '۰۱۲۳۴۵۶۷۸۹' for c in result)}")
print(f"Contains Persian month: {'اردیبهشت' in result or 'خرداد' in result or 'تیر' in result}")
