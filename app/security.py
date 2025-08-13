import bcrypt, jwt
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

def create_access_token(sub: str, role: str) -> str:
    exp = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": sub, "role": role, "exp": exp}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGO)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
