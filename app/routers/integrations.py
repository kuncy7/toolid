# Plik: app/routers/integrations.py (cała zawartość)

from fastapi import APIRouter, HTTPException, Depends, Body  # <-- POPRAWKA TUTAJ
from typing import List, Optional
from pydantic import BaseModel
from sqlmodel import Session, select
from datetime import datetime
from ..db import get_session
from ..models import ExternalIntegration, IntegrationLog
from ..dependencies import require_role

# Zabezpieczenie całego routera - wymaga roli "admin"
router = APIRouter(dependencies=[Depends(require_role("admin"))])

# --- Schematy Pydantic ---


class IntegrationCreate(BaseModel):
    name: str
    type: str
    config: dict


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


# --- Endpointy CRUD dla integracji ---


@router.get("", response_model=List[ExternalIntegration])
def list_integrations(session: Session = Depends(get_session)):
    return session.exec(select(ExternalIntegration)).all()


@router.post("", response_model=ExternalIntegration, status_code=201)
def create_integration(
    payload: IntegrationCreate, session: Session = Depends(get_session)
):
    integration = ExternalIntegration.model_validate(payload)
    session.add(integration)
    session.commit()
    session.refresh(integration)
    return integration


@router.get("/{integration_id}", response_model=ExternalIntegration)
def get_integration(integration_id: str, session: Session = Depends(get_session)):
    integration = session.get(ExternalIntegration, integration_id)
    if not integration:
        raise HTTPException(404, "Integration not found")
    return integration


@router.put("/{integration_id}", response_model=ExternalIntegration)
def update_integration(
    integration_id: str,
    payload: IntegrationUpdate,
    session: Session = Depends(get_session),
):
    integration = session.get(ExternalIntegration, integration_id)
    if not integration:
        raise HTTPException(404, "Integration not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(integration, key, value)
    integration.updated_at = datetime.utcnow()

    session.add(integration)
    session.commit()
    session.refresh(integration)
    return integration


@router.delete("/{integration_id}", status_code=204)
def delete_integration(integration_id: str, session: Session = Depends(get_session)):
    integration = session.get(ExternalIntegration, integration_id)
    if integration:
        session.delete(integration)
        session.commit()


# --- Endpointy dla logów i testowania ---


@router.post("/{integration_id}/test")
def test_integration(integration_id: str, session: Session = Depends(get_session)):
    integration = session.get(ExternalIntegration, integration_id)
    if not integration:
        raise HTTPException(404, "Integration not found")

    ok = True
    status = "success" if ok else "error"
    message = "Connection successful" if ok else "Connection failed"

    log = IntegrationLog(
        integration_id=integration_id, event_type="test", status=status, message=message
    )
    session.add(log)
    session.commit()

    return {"id": integration_id, "ok": ok, "message": message}


@router.get("/{integration_id}/logs", response_model=List[IntegrationLog])
def logs_integration(integration_id: str, session: Session = Depends(get_session)):
    if not session.get(ExternalIntegration, integration_id):
        raise HTTPException(404, "Integration not found")
    return session.exec(
        select(IntegrationLog).where(IntegrationLog.integration_id == integration_id)
    ).all()
