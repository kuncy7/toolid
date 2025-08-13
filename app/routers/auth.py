from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from datetime import datetime
from sqlmodel import select
from ..db import get_session
from ..models import User
from ..security import verify_password, create_access_token

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
    session = Depends(get_session),
):
    s = session
    user = s.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    user.last_login = datetime.utcnow()
    s.add(user); s.commit()
    token = create_access_token(sub=user.id, role=user.role)
    return TokenOut(access_token=token)
