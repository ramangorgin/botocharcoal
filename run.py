# run.py
import uvicorn
import os
import sys

# اضافه کردن مسیر جاری به سیستم برای شناسایی پکیج app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8080, reload=True)
