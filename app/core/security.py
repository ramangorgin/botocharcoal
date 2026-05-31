import secrets
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_serializer = URLSafeTimedSerializer(settings.SECRET_KEY)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_session_token(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id}, salt="admin-session")


def verify_session_token(token: str, max_age: int = None) -> dict | None:
    try:
        max_age = max_age or settings.ADMIN_SESSION_MAX_AGE
        return _serializer.loads(token, salt="admin-session", max_age=max_age)
    except Exception:
        return None


def generate_csrf_token() -> str:
    return secrets.token_hex(32)
