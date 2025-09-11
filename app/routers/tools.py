# Plik: app/routers/tools.py

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from pydantic import BaseModel, computed_field, ConfigDict
from datetime import datetime
from sqlmodel import Session, select
from pathlib import Path
import shutil
import re
import base64
import uuid
from PIL import Image
from io import BytesIO

from ..db import get_session
from ..models import Tool as ToolModel, ToolLoan, ToolWeight, User
from ..dependencies import require_role, get_current_user
from ..config import settings
from ..exceptions import ResourceNotFound, OperationForbidden

router = APIRouter()

# --- Schematy Pydantic dla operacji wejściowych ---


class ToolCreate(BaseModel):
    name: str
    quantity_total: int = 1
    weight_value: Optional[float] = None
    weight_unit: str = "g"
    width: Optional[float] = None
    height: Optional[float] = None
    area: Optional[float] = None
    diameter: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = "w magazynie"
    condition: Optional[str] = None
    image_url: Optional[str] = None


class ToolUpdate(BaseModel):
    name: Optional[str] = None
    quantity_total: Optional[int] = None
    weight_value: Optional[float] = None
    weight_unit: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    area: Optional[float] = None
    diameter: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None  # To pole jest ignorowane przy aktualizacji
    condition: Optional[str] = None
    image_url: Optional[str] = None


class WeightCreate(BaseModel):
    weight_value: float


class LocalImagePayload(BaseModel):
    local_path: str


class Base64ImagePayload(BaseModel):
    image_data: str


class Message(BaseModel):
    message: str


class ToolReturnPayload(BaseModel):
    tool_id: int


# --- Schemat odpowiedzi API ---
class ToolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    quantity_total: int
    quantity_available: int
    weight_value: Optional[float] = None
    weight_unit: str
    width: Optional[float] = None
    height: Optional[float] = None
    area: Optional[float] = None
    diameter: Optional[str] = None
    type: Optional[str] = None
    condition: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def status(self) -> str:
        qty = self.quantity_available
        if qty <= 0:
            return "brak w magazynie"
        if qty == 1:
            return "w magazynie 1 sztuka"
        if qty % 10 in [2, 3, 4] and qty not in [12, 13, 14]:
            return f"w magazynie {qty} sztuki"
        return f"w magazynie {qty} sztuk"


# --- Endpointy API ---


@router.get("", response_model=List[ToolOut], dependencies=[Depends(get_current_user)])
def list_tools(session: Session = Depends(get_session)):
    tools = session.exec(select(ToolModel)).all()
    return tools


@router.post(
    "",
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

    obj.updated_at = datetime.now()  # <-- POPRAWKA: Jawne ustawienie daty modyfikacji
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


# --- Endpoint do zwrotu narzędzia ---
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
    tool.updated_at = datetime.now()  # <-- POPRAWKA: Aktualizujemy też narzędzie

    session.add(loan_to_return)
    session.add(tool)
    session.commit()
    session.refresh(loan_to_return)

    return loan_to_return


# --- Endpointy dla Zdjęć ---
@router.post(
    "/{tool_id}/upload-base64-image",
    response_model=ToolOut,
    dependencies=[Depends(require_role("admin", "moderator"))],
)
def upload_base64_image(
    tool_id: int, payload: Base64ImagePayload, session: Session = Depends(get_session)
):
    tool = session.get(ToolModel, tool_id)
    if not tool:
        raise ResourceNotFound(name="Tool", resource_id=tool_id)
    try:
        header, encoded_data = payload.image_data.split(",", 1)
        match = re.search(r"data:image/(?P<ext>jpeg|png|gif)", header)
        if not match:
            raise OperationForbidden(
                reason="Invalid image format. Only jpeg, png, gif are supported."
            )
        file_extension = "." + match.group("ext")
        image_bytes = base64.b64decode(encoded_data)
    except (ValueError, TypeError) as e:
        raise OperationForbidden(reason=f"Invalid Base64 data: {e}")
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    image_dir = Path("static/images")
    image_dir.mkdir(exist_ok=True)

    image_path = image_dir / unique_filename

    try:
        with Image.open(BytesIO(image_bytes)) as img:
            img.save(image_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and save image: {e}",
        )

    tool.image_url = f"/static/images/{unique_filename}"
    tool.updated_at = datetime.now()  # <-- POPRAWKA: Jawne ustawienie daty modyfikacji
    session.add(tool)
    session.commit()
    session.refresh(tool)
    return tool


@router.post(
    "/{tool_id}/assign-local-image",
    response_model=ToolOut,
    dependencies=[Depends(require_role("admin", "moderator"))],
)
def assign_local_image(
    tool_id: int, payload: LocalImagePayload, session: Session = Depends(get_session)
):
    tool = session.get(ToolModel, tool_id)
    if not tool:
        raise ResourceNotFound(name="Tool", resource_id=tool_id)
    source_path = Path(payload.local_path)
    if not source_path.is_file():
        raise ResourceNotFound(name="Source file", resource_id=str(source_path))
    allowed_path = Path(settings.ALLOWED_LOCAL_PATH).resolve()
    if not source_path.resolve().is_relative_to(allowed_path):
        raise OperationForbidden(reason="File path is outside the allowed directory.")
    upload_dir = Path("static/images")
    upload_dir.mkdir(exist_ok=True)
    file_extension = source_path.suffix
    new_filename = f"{uuid.uuid4()}{file_extension}"
    destination_path = upload_dir / new_filename
    try:
        shutil.copy(source_path, destination_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to copy file: {e}",
        )
    tool.image_url = f"/static/images/{new_filename}"
    tool.updated_at = datetime.now()  # <-- POPRAWKA: Jawne ustawienie daty modyfikacji
    session.add(tool)
    session.commit()
    session.refresh(tool)
    return tool


# --- Endpointy dla Wypożyczeń ---
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
    tool.updated_at = datetime.now()  # <-- POPRAWKA: Aktualizujemy też narzędzie
    session.add(tool)

    loan = ToolLoan(tool_id=tool_id, user_id=user_id)
    session.add(loan)
    session.commit()
    session.refresh(loan)
    return loan


# --- Endpointy dla Pomiarów Wagi ---
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
