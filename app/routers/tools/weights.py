# Plik: app/routers/tools/weights.py

from fastapi import APIRouter, Depends
from typing import List
from sqlmodel import Session, select

from ...db import get_session
from ...models import Tool as ToolModel, ToolWeight
from ...dependencies import get_current_user
from ...exceptions import ResourceNotFound
from .schemas import WeightCreate

router = APIRouter()


@router.get(
    "/{tool_id}/weights",
    response_model=List[ToolWeight],
    dependencies=[Depends(get_current_user)],
)
def get_tool_weights_history(tool_id: int, session: Session = Depends(get_session)):
    weights = session.exec(
        select(ToolWeight).where(ToolWeight.tool_id == tool_id)
    ).all()
    return weights


@router.post(
    "/{tool_id}/weights",
    response_model=ToolWeight,
    status_code=201,
    dependencies=[Depends(get_current_user)],
)
def add_weight_measurement(
    tool_id: int,
    payload: WeightCreate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    if not session.get(ToolModel, tool_id):
        raise ResourceNotFound(name="Tool", resource_id=tool_id)

    measurement = ToolWeight(
        tool_id=tool_id,
        weight_value=payload.weight_value,
        measured_by=current_user.get("sub"),
    )
    session.add(measurement)
    session.commit()
    session.refresh(measurement)
    return measurement
