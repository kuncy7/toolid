from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional
from pydantic import BaseModel
from datetime import date
from sqlmodel import select
from ..db import get_session
from ..models import Tool, ToolLoan
from ..dependencies import require_role

router = APIRouter()

class LoanCreate(BaseModel):
    user_id: str

class ToolCreate(BaseModel):
    name: str
    dimensions: Optional[str] = None
    diameter: Optional[str] = None
    weight: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    condition: Optional[str] = None
    image_url: Optional[str] = None

class ToolUpdate(BaseModel):
    name: Optional[str] = None
    dimensions: Optional[str] = None
    diameter: Optional[str] = None
    weight: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    condition: Optional[str] = None
    image_url: Optional[str] = None

@router.get("", response_model=List[Tool])
def list_tools(session = Depends(get_session)):
    s = session
    return s.exec(select(Tool)).all()

@router.post("", response_model=Tool, status_code=201)
def create_tool(
    payload: ToolCreate = Body(..., example={
        "name": "Klucz dynamometryczny 1/2",
        "dimensions": "350mm",
        "weight": "1.2kg",
        "type": "wrench",
        "status": "available",
        "condition": "good",
        "image_url": "https://example.com/img/wrench.jpg"
    }),
    session = Depends(get_session),
    _=Depends(require_role("admin","moderator")),
):
    s = session
    obj = Tool(**payload.model_dump(exclude_unset=True))
    s.add(obj); s.commit(); s.refresh(obj); return obj

@router.get("/{tool_id}", response_model=Tool)
def get_tool(tool_id: int, session = Depends(get_session)):
    s = session
    obj = s.get(Tool, tool_id)
    if not obj: raise HTTPException(404, "Tool not found")
    return obj

@router.put("/{tool_id}", response_model=Tool)
def update_tool(
    tool_id: int,
    data: ToolUpdate = Body(..., example={"status": "in_use", "condition": "worn", "dimensions": "355mm"}),
    session = Depends(get_session),
    _=Depends(require_role("admin","moderator")),
):
    s = session
    obj = s.get(Tool, tool_id)
    if not obj: raise HTTPException(404, "Tool not found")
    for k,v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    s.add(obj); s.commit(); s.refresh(obj); return obj

@router.get("/{tool_id}/loans", response_model=List[ToolLoan])
def tool_loans(tool_id: int, session = Depends(get_session)):
    s = session
    return s.exec(select(ToolLoan).where(ToolLoan.tool_id==tool_id)).all()

@router.post("/{tool_id}/loans", response_model=ToolLoan, status_code=201)
def create_loan(
    tool_id: int,
    payload: LoanCreate = Body(..., example={"user_id": "6f8a5d9c-1b2f-4e3a-9c0d-1234567890ab"}),
    session = Depends(get_session),
):
    s = session
    loan = ToolLoan(tool_id=tool_id, user_id=payload.user_id, loan_date=date.today())
    s.add(loan); s.commit(); s.refresh(loan); return loan
