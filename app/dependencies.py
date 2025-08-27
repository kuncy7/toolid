# Plik: app/dependencies.py (cała zawartość)

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from .security import decode_token
from .db import get_session
from .models import UserSession # Import modelu sesji

bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    session: Session = Depends(get_session)
):
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_token(creds.credentials)
        token_jti = payload.get("jti")
        if not token_jti:
            raise HTTPException(401, "Invalid token format")
    except Exception:
        raise HTTPException(401, "Invalid token")

    # Sprawdzenie, czy sesja jest aktywna w bazie danych
    db_session = session.exec(
        select(UserSession).where(UserSession.id == token_jti)
    ).first()

    if not db_session or not db_session.is_active:
        raise HTTPException(401, "Session is not active")

    return payload  # {sub, role, exp, jti}

def require_role(*roles: str):
    def _checker(user = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(403, "Forbidden")
        return user
    return _checker
