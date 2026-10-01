import os
import secrets
from datetime import timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE = os.path.join(ROOT, "instance")


def _secret() -> str:
    os.makedirs(INSTANCE, exist_ok=True)
    path = os.path.join(INSTANCE, "secret_key")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            saved = handle.read().strip()
            if saved:
                return saved
    key = secrets.token_hex(32)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(key)
    return key


class Config:
    SECRET_KEY = _secret()
    JSON_AS_ASCII = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    DATABASE = os.path.join(INSTANCE, "liga.sqlite")
    AVATARS = os.path.join(INSTANCE, "avatars")
