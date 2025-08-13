from fastapi import APIRouter, Body
from pydantic import BaseModel

class WarehouseConfigPayload(BaseModel):
    provider: str
    options: dict

class OrderCreate(BaseModel):
    external_id: str
    items: list  # [{"tool_id": 1, "qty": 2}, ...]

class ToolMappingCreate(BaseModel):
    external_tool_id: str
    internal_tool_id: int

router = APIRouter()

@router.get("/config")
async def get_config():
    return {"status": "todo"}

@router.put("/config")
async def update_config(
    payload: WarehouseConfigPayload = Body(..., example={
        "provider": "ExternalAPI",
        "options": {"base_url": "https://warehouse.example.com/api", "token": "****"}
    })
):
    return {"status": "todo", "received": payload.model_dump()}

@router.get("/orders")
async def list_orders():
    return []

@router.post("/orders")
async def create_order(
    payload: OrderCreate = Body(..., example={
        "external_id": "PO-2025-0001",
        "items": [{"tool_id": 1, "qty": 2}, {"tool_id": 5, "qty": 1}]
    })
):
    return {"status": "todo", "received": payload.model_dump()}

@router.get("/tool-mapping")
async def list_mapping():
    return []

@router.post("/tool-mapping")
async def create_mapping(
    payload: ToolMappingCreate = Body(..., example={
        "external_tool_id": "ERP-TOOL-001",
        "internal_tool_id": 42
    })
):
    return {"status": "todo", "received": payload.model_dump()}
