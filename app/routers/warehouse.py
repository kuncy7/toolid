# Plik: app/routers/warehouse.py (cała zawartość)

from fastapi import APIRouter, HTTPException, Depends, Body # <-- POPRAWKA TUTAJ
from typing import List, Optional
from pydantic import BaseModel
from sqlmodel import Session, select
from datetime import datetime
from ..db import get_session
from ..models import WarehouseConfig, ToolOrder, ToolMapping, Tool
from ..dependencies import require_role

# Zabezpieczenie całego routera - wymaga roli "admin"
router = APIRouter(dependencies=[Depends(require_role("admin"))])

# --- Schematy Pydantic ---

class WarehouseConfigPayload(BaseModel):
    provider: str
    options: dict

class OrderCreate(BaseModel):
    external_id: Optional[str] = None
    items: list

class ToolMappingCreate(BaseModel):
    external_tool_id: str
    internal_tool_id: int

# --- Endpointy dla konfiguracji ---

@router.get("/config", response_model=Optional[WarehouseConfig])
def get_config(session: Session = Depends(get_session)):
    return session.exec(select(WarehouseConfig)).first()

@router.put("/config", response_model=WarehouseConfig)
def update_config(payload: WarehouseConfigPayload, session: Session = Depends(get_session)):
    config = session.exec(select(WarehouseConfig)).first()
    if not config:
        config = WarehouseConfig(**payload.model_dump())
    else:
        update_data = payload.model_dump()
        for key, value in update_data.items():
            setattr(config, key, value)
        config.updated_at = datetime.utcnow()
    
    session.add(config)
    session.commit()
    session.refresh(config)
    return config

# --- Endpointy dla zamówień ---

@router.get("/orders", response_model=List[ToolOrder])
def list_orders(session: Session = Depends(get_session)):
    return session.exec(select(ToolOrder)).all()

@router.post("/orders", response_model=ToolOrder, status_code=201)
def create_order(payload: OrderCreate, session: Session = Depends(get_session)):
    order = ToolOrder.model_validate(payload)
    session.add(order)
    session.commit()
    session.refresh(order)
    return order

# --- Endpointy dla mapowania narzędzi ---

@router.get("/tool-mapping", response_model=List[ToolMapping])
def list_mapping(session: Session = Depends(get_session)):
    return session.exec(select(ToolMapping)).all()

@router.post("/tool-mapping", response_model=ToolMapping, status_code=201)
def create_mapping(payload: ToolMappingCreate, session: Session = Depends(get_session)):
    if not session.get(Tool, payload.internal_tool_id):
        raise HTTPException(404, "Internal tool not found")
    
    existing = session.exec(select(ToolMapping).where(ToolMapping.external_tool_id == payload.external_tool_id)).first()
    if existing:
        raise HTTPException(400, f"External tool ID '{payload.external_tool_id}' is already mapped.")

    mapping = ToolMapping.model_validate(payload)
    session.add(mapping)
    session.commit()
    session.refresh(mapping)
    return mapping

@router.delete("/tool-mapping/{mapping_id}", status_code=204)
def delete_mapping(mapping_id: int, session: Session = Depends(get_session)):
    mapping = session.get(ToolMapping, mapping_id)
    if mapping:
        session.delete(mapping)
        session.commit()
