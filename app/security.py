# Plik: app/security.py (cała zawartość)

import bcrypt, jwt, uuid
from datetime import datetime, timedelta
from .config import settings

ALGO = "HS256"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), password_hash.encode())
    except Exception:
        return False


def create_access_token(sub: str, role: str) -> tuple[str, str, datetime]:
    """Zwraca token, jego unikalne ID (jti) oraz datę wygaśnięcia."""
    exp = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    jti = str(uuid.uuid4())
    payload = {
        "sub": sub,
        "role": role,
        "exp": exp,
        "jti": jti,  # Unikalny identyfikator tokena
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGO)
    return token, jti, exp


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
