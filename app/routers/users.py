from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional
from pydantic import BaseModel
from sqlmodel import select
from ..db import get_session
from ..models import User
from ..security import hash_password
from ..dependencies import require_role
import uuid

router = APIRouter()

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    role: Optional[str] = "user"
    status: Optional[str] = "active"

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

@router.get("", response_model=List[User])
def list_users(session = Depends(get_session), _=Depends(require_role("admin"))):
    s = session
    return s.exec(select(User)).all()

@router.post("", response_model=User, status_code=201)
def create_user(
    u: UserCreate = Body(..., example={
        "first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com", "password": "S3cret!", "role": "user", "status": "active"
    }),
    session = Depends(get_session),
    _=Depends(require_role("admin")),
):
    s = session
    user = User(
        id=str(uuid.uuid4()),
        first_name=u.first_name,
        last_name=u.last_name,
        email=u.email,
        password_hash=hash_password(u.password),
        role=u.role or "user",
        status=u.status or "active",
    )
    s.add(user); s.commit(); s.refresh(user)
    return user

@router.get("/{user_id}", response_model=User)
def get_user(user_id: str, session = Depends(get_session), _=Depends(require_role("admin","moderator"))):
    s = session
    obj = s.get(User, user_id)
    if not obj: raise HTTPException(404, "User not found")
    return obj

@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: str,
    data: UserUpdate = Body(..., example={"first_name": "Ada", "last_name": "Byron", "password": "N3wP@ss", "role": "moderator"}),
    session = Depends(get_session),
    _=Depends(require_role("admin")),
):
    s = session
    obj = s.get(User, user_id)
    if not obj: raise HTTPException(404, "User not found")
    upd = data.model_dump(exclude_unset=True)
    if "password" in upd and upd["password"]:
        upd["password_hash"] = hash_password(upd.pop("password"))
    for k,v in upd.items():
        setattr(obj, k, v)
    s.add(obj); s.commit(); s.refresh(obj); return obj

@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: str, session = Depends(get_session), _=Depends(require_role("admin"))):
    s = session
    obj = s.get(User, user_id)
    if obj:
        s.delete(obj); s.commit()
