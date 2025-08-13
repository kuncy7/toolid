from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from pydantic.config import ConfigDict
from datetime import datetime
from sqlmodel import select
from ..db import get_session
from ..models import ScaleConfig
import serial

router = APIRouter()

class ScaleConfigPayload(BaseModel):
    # ignoruj nadmiarowe pola (np. updated_at/id) i pokaż przykład w docs
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "port": "/dev/ttyUSB0",
                "baudrate": 9600,
                "parity": "N",
                "data_bits": 8,
                "stop_bits": 1,
                "timeout": 5000
            }
        },
    )
    port: str
    baudrate: int
    parity: str  # "N" | "E" | "O"
    data_bits: int
    stop_bits: int
    timeout: int  # ms

@router.get("/config", response_model=ScaleConfig)
def get_config(session = Depends(get_session)):
    s = session
    cfg = s.exec(select(ScaleConfig)).first()
    if not cfg:
        cfg = ScaleConfig()
        s.add(cfg); s.commit(); s.refresh(cfg)
    return cfg

@router.put("/config", response_model=ScaleConfig)
def update_config(
    payload: ScaleConfigPayload = Body(...),
    session = Depends(get_session),
):
    s = session
    cfg = s.exec(select(ScaleConfig)).first()
    if not cfg:
        cfg = ScaleConfig(**payload.model_dump())
    else:
        for k, v in payload.model_dump().items():
            setattr(cfg, k, v)
    cfg.updated_at = datetime.utcnow()
    s.add(cfg); s.commit(); s.refresh(cfg); return cfg

@router.get("/read")
def read_once(session = Depends(get_session)):
    s = session
    cfg = s.exec(select(ScaleConfig)).first()
    if not cfg: raise HTTPException(404, "No scale config")
    ser = serial.Serial(cfg.port, cfg.baudrate, timeout=cfg.timeout/1000.0)
    raw = ser.readline().decode(errors="ignore").strip()
    ser.close()
    return {"raw": raw}
