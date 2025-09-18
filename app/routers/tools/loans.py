# Plik: app/routers/tools/loans.py

from fastapi import APIRouter, Depends
from typing import List
from sqlmodel import Session, select
from datetime import datetime

from ...db import get_session
from ...models import Tool as ToolModel, ToolLoan, User
from ...dependencies import require_role, get_current_user
from ...exceptions import ResourceNotFound, OperationForbidden
from .schemas import ToolReturnPayload

router = APIRouter()


@router.post(
    "/return",
    response_model=ToolLoan,
    dependencies=[Depends(require_role("admin", "moderator"))],
)
def return_tool(payload: ToolReturnPayload, session: Session = Depends(get_session)):
    tool = session.get(ToolModel, payload.tool_id)
    if not tool:
        raise ResourceNotFound(name="Tool", resource_id=payload.tool_id)

    if tool.quantity_available >= tool.quantity_total:
        raise OperationForbidden(
            reason="Cannot return tool: all items are already in stock."
        )

    loan_to_return = session.exec(
        select(ToolLoan)
        .where(ToolLoan.tool_id == payload.tool_id)
        .where(ToolLoan.returned == False)
        .order_by(ToolLoan.loan_date)
    ).first()

    if not loan_to_return:
        raise ResourceNotFound(
            name="Active loan for this tool", resource_id=payload.tool_id
        )

    loan_to_return.returned = True
    loan_to_return.return_date = datetime.now()
    tool.quantity_available += 1
    tool.updated_at = datetime.now()

    session.add(loan_to_return)
    session.add(tool)
    session.commit()
    session.refresh(loan_to_return)

    return loan_to_return


@router.get(
    "/{tool_id}/loans",
    response_model=List[ToolLoan],
    dependencies=[Depends(require_role("admin", "moderator"))],
)
def tool_loans(tool_id: int, session: Session = Depends(get_session)):
    return session.exec(select(ToolLoan).where(ToolLoan.tool_id == tool_id)).all()


@router.post(
    "/{tool_id}/loans",
    response_model=ToolLoan,
    status_code=201,
    dependencies=[Depends(get_current_user)],
)
def create_loan(
    tool_id: int,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    tool = session.get(ToolModel, tool_id)
    if not tool:
        raise ResourceNotFound(name="Tool", resource_id=tool_id)

    user_id = current_user.get("sub")
    if not session.get(User, user_id):
        raise ResourceNotFound(name="User", resource_id=user_id)

    if tool.quantity_available <= 0:
        raise OperationForbidden(reason="No available items for this tool.")

    tool.quantity_available -= 1
    tool.updated_at = datetime.now()
    session.add(tool)

    loan = ToolLoan(tool_id=tool_id, user_id=user_id)
    session.add(loan)
    session.commit()
    session.refresh(loan)
    return loan
