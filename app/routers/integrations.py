from fastapi import APIRouter, Body
from pydantic import BaseModel

class IntegrationCreate(BaseModel):
    name: str
    type: str  # np. webhook/rest
    config: dict

router = APIRouter()

@router.get("")
async def list_integrations():
    return []

@router.post("")
async def create_integration(
    payload: IntegrationCreate = Body(..., example={
        "name": "ERP Hook",
        "type": "webhook",
        "config": {"url": "https://erp.example.com/hook", "secret": "****"}
    })
):
    return {"status": "todo", "received": payload.model_dump()}

@router.get("/{integration_id}")
async def get_integration(integration_id: int):
    return {"id": integration_id}

@router.post("/{integration_id}/test")
async def test_integration(integration_id: int):
    return {"id": integration_id, "ok": True}

@router.get("/{integration_id}/logs")
async def logs_integration(integration_id: int):
    return []
