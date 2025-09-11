# Plik: app/routers/scale.py (poprawiona, działająca zawartość)

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from pydantic.config import ConfigDict
from datetime import datetime
from sqlmodel import Session, select
from ..db import get_session
from ..models import ScaleConfig, ScaleWeight
from ..dependencies import (
    require_role,
    get_current_user,
)  # Upewnij się, że get_current_user jest importowane
import serial

router = APIRouter()


class ScaleConfigPayload(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "port": "/dev/ttyUSB0",
                "baudrate": 9600,
                "parity": "N",
                "data_bits": 8,
                "stop_bits": 1,
                "timeout": 5000,
            }
        },
    )
    port: str
    baudrate: int
    parity: str
    data_bits: int
    stop_bits: int
    timeout: int


@router.get(
    "/config", response_model=ScaleConfig, dependencies=[Depends(require_role("admin"))]
)
def get_config(session: Session = Depends(get_session)):
    s = session
    cfg = s.exec(select(ScaleConfig)).first()
    if not cfg:
        cfg = ScaleConfig()
        s.add(cfg)
        s.commit()
        s.refresh(cfg)
    return cfg


@router.put(
    "/config", response_model=ScaleConfig, dependencies=[Depends(require_role("admin"))]
)
def update_config(
    payload: ScaleConfigPayload = Body(...),
    session: Session = Depends(get_session),
):
    s = session
    cfg = s.exec(select(ScaleConfig)).first()
    if not cfg:
        cfg = ScaleConfig(**payload.model_dump())
    else:
        for k, v in payload.model_dump().items():
            setattr(cfg, k, v)
    cfg.updated_at = datetime.utcnow()
    s.add(cfg)
    s.commit()
    s.refresh(cfg)
    return cfg


@router.get("/read", dependencies=[Depends(get_current_user)])
def read_once(session: Session = Depends(get_session)):
    """Wymaga tylko bycia zalogowanym."""
    s = session
    cfg = s.exec(select(ScaleConfig)).first()
    if not cfg:
        raise HTTPException(404, "No scale config")
    try:
        ser = serial.Serial(cfg.port, cfg.baudrate, timeout=cfg.timeout / 1000.0)
        raw = ser.readline().decode(errors="ignore").strip()
        ser.close()
    except serial.SerialException as e:
        raise HTTPException(status_code=500, detail=f"Scale connection error: {e}")
    return {"raw": raw}


# --- ENDPOINT Z ZABEZPIECZENIEM ---
@router.get(
    "/weight/{scale_id}/last",
    response_model=ScaleWeight,
    dependencies=[Depends(get_current_user)],  # <-- POPRAWKA JEST TUTAJ
)
def get_last_weight(scale_id: int, session: Session = Depends(get_session)):
    """
    Pobiera ostatni zarejestrowany pomiar wagi dla określonej wagi.
    Wymaga bycia zalogowanym.
    """
    weight = session.exec(
        select(ScaleWeight)
        .where(ScaleWeight.scale_id == scale_id)
        .order_by(ScaleWeight.created_at.desc())  # type: ignore
    ).first()

    if not weight:
        raise HTTPException(
            status_code=404, detail="No weight readings found for this scale"
        )

    return weight
