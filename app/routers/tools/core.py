# Plik: app/routers/tools/core.py

from fastapi import APIRouter, Depends
from typing import List
from sqlmodel import Session, select
from datetime import datetime

from ...db import get_session
from ...models import Tool as ToolModel, ToolLoan
from ...dependencies import require_role, get_current_user
from ...exceptions import ResourceNotFound, OperationForbidden
from .schemas import ToolCreate, ToolUpdate, ToolOut, Message

router = APIRouter()


@router.get("/", response_model=List[ToolOut], dependencies=[Depends(get_current_user)])
def list_tools(session: Session = Depends(get_session)):
    tools = session.exec(select(ToolModel)).all()
    return tools


@router.post(
    "/",
    response_model=ToolOut,
    status_code=201,
    dependencies=[Depends(require_role("admin", "moderator"))],
)
def create_tool(payload: ToolCreate, session: Session = Depends(get_session)):
    obj_data = payload.model_dump()
    obj_data["quantity_available"] = payload.quantity_total
    obj = ToolModel.model_validate(obj_data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


@router.get(
    "/{tool_id}", response_model=ToolOut, dependencies=[Depends(get_current_user)]
)
def get_tool(tool_id: int, session: Session = Depends(get_session)):
    obj = session.get(ToolModel, tool_id)
    if not obj:
        raise ResourceNotFound(name="Tool", resource_id=tool_id)
    return obj


@router.put(
    "/{tool_id}",
    response_model=ToolOut,
    dependencies=[Depends(require_role("admin", "moderator"))],
)
def update_tool(
    tool_id: int, data: ToolUpdate, session: Session = Depends(get_session)
):
    obj = session.get(ToolModel, tool_id)
    if not obj:
        raise ResourceNotFound(name="Tool", resource_id=tool_id)

    update_data = data.model_dump(exclude_unset=True)
    if "quantity_total" in update_data:
        new_total = update_data["quantity_total"]
        loaned_count = obj.quantity_total - obj.quantity_available
        if new_total < loaned_count:
            raise OperationForbidden(
                f"Cannot set total quantity to {new_total}, because {loaned_count} items are currently on loan."
            )
        obj.quantity_available = new_total - loaned_count

    update_data.pop("status", None)

    for k, v in update_data.items():
        setattr(obj, k, v)

    obj.updated_at = datetime.now()
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


@router.delete(
    "/{tool_id}",
    response_model=Message,
    dependencies=[Depends(require_role("admin", "moderator"))],
)
def delete_tool(tool_id: int, session: Session = Depends(get_session)):
    tool = session.get(ToolModel, tool_id)
    if not tool:
        raise ResourceNotFound(name="Tool", resource_id=tool_id)

    active_loans = session.exec(
        select(ToolLoan).where(ToolLoan.tool_id == tool_id, ToolLoan.returned == False)
    ).all()

    if active_loans:
        raise OperationForbidden(
            f"Cannot delete tool. There are {len(active_loans)} active loans."
        )

    session.delete(tool)
    session.commit()
    return {"message": "Tool deleted successfully"}
