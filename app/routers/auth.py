# Plik: app/routers/auth.py (cała zawartość)

from fastapi import APIRouter, HTTPException, Depends, Body, status
from pydantic import BaseModel
from datetime import datetime
from sqlmodel import Session, select
from ..db import get_session
from ..models import User, UserSession
from ..security import verify_password, create_access_token
from ..dependencies import get_current_user

router = APIRouter()

class LoginIn(BaseModel):
    email: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenOut)
def login(
    payload: LoginIn = Body(..., example={"email": "admin@example.com", "password": "admin"}),
    session: Session = Depends(get_session),
):
    s = session
    user = s.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    
    # Utworzenie tokena i sesji w bazie danych
    token, jti, exp = create_access_token(sub=user.id, role=user.role)
    
    # === POPRAWKA JEST TUTAJ ===
    # Dodajemy `session_token=token` do tworzonego obiektu.
    user_session = UserSession(id=jti, user_id=user.id, session_token=token, expires_at=exp)
    s.add(user_session)
    
    user.last_login = datetime.utcnow()
    s.add(user)
    s.commit()
    
    return TokenOut(access_token=token)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    """Unieważnia bieżącą sesję użytkownika."""
    token_jti = current_user.get("jti")
    db_session = session.get(UserSession, token_jti)
    if db_session:
        db_session.is_active = False
        session.add(db_session)
        session.commit()
