# Plik: app/routers/users.py (cała, zaktualizowana zawartość)

from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional
from pydantic import BaseModel
from sqlmodel import Session, select
from ..db import get_session
from ..models import User, UserPermission
from ..security import hash_password
from ..dependencies import require_role
import uuid

router = APIRouter()

# --- Schematy Pydantic ---


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


class PermissionUpdate(BaseModel):
    module: str
    permission: str
    granted: bool


class PasswordReset(BaseModel):
    new_password: str


# --- Endpointy CRUD dla użytkowników ---


@router.get(
    "", response_model=List[User], dependencies=[Depends(require_role("admin"))]
)
def list_users(session: Session = Depends(get_session)):
    return session.exec(select(User)).all()


@router.post(
    "",
    response_model=User,
    status_code=201,
    dependencies=[Depends(require_role("admin"))],
)
def create_user(u: UserCreate, session: Session = Depends(get_session)):
    user = User(
        id=str(uuid.uuid4()),
        first_name=u.first_name,
        last_name=u.last_name,
        email=u.email,
        password_hash=hash_password(u.password),
        role=u.role or "user",
        status=u.status or "active",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.get(
    "/{user_id}",
    response_model=User,
    dependencies=[Depends(require_role("admin", "moderator"))],
)
def get_user(user_id: str, session: Session = Depends(get_session)):
    obj = session.get(User, user_id)
    if not obj:
        raise HTTPException(404, "User not found")
    return obj


@router.put(
    "/{user_id}", response_model=User, dependencies=[Depends(require_role("admin"))]
)
def update_user(
    user_id: str, data: UserUpdate, session: Session = Depends(get_session)
):
    obj = session.get(User, user_id)
    if not obj:
        raise HTTPException(404, "User not found")
    upd = data.model_dump(exclude_unset=True)
    if "password" in upd and upd["password"]:
        upd["password_hash"] = hash_password(upd.pop("password"))
    for k, v in upd.items():
        setattr(obj, k, v)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


# --- NOWY ENDPOINT DO RESETOWANIA HASŁA ---
@router.post(
    "/{user_id}/reset-password",
    status_code=204,
    dependencies=[Depends(require_role("admin"))],
)
def reset_password(
    user_id: str, payload: PasswordReset, session: Session = Depends(get_session)
):
    """Resetuje hasło dla wybranego użytkownika (tylko admin)."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    session.add(user)
    session.commit()
    return


@router.delete(
    "/{user_id}", status_code=204, dependencies=[Depends(require_role("admin"))]
)
def delete_user(user_id: str, session: Session = Depends(get_session)):
    obj = session.get(User, user_id)
    if obj:
        session.delete(obj)
        session.commit()


# --- Endpointy dla uprawnień ---


@router.get(
    "/{user_id}/permissions",
    response_model=List[UserPermission],
    dependencies=[Depends(require_role("admin"))],
)
def get_user_permissions(user_id: str, session: Session = Depends(get_session)):
    if not session.get(User, user_id):
        raise HTTPException(404, "User not found")
    return session.exec(
        select(UserPermission).where(UserPermission.user_id == user_id)
    ).all()


@router.put(
    "/{user_id}/permissions",
    response_model=UserPermission,
    dependencies=[Depends(require_role("admin"))],
)
def update_user_permission(
    user_id: str, payload: PermissionUpdate, session: Session = Depends(get_session)
):
    if not session.get(User, user_id):
        raise HTTPException(404, "User not found")
    permission = session.exec(
        select(UserPermission)
        .where(UserPermission.user_id == user_id)
        .where(UserPermission.module == payload.module)
        .where(UserPermission.permission == payload.permission)
    ).first()
    if permission:
        permission.granted = payload.granted
    else:
        permission = UserPermission(user_id=user_id, **payload.model_dump())
    session.add(permission)
    session.commit()
    session.refresh(permission)
    return permission
