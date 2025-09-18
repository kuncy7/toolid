# Plik: app/routers/tools/schemas.py

from pydantic import BaseModel, computed_field, ConfigDict
from typing import Optional
from datetime import datetime


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
    icons_url: Optional[str] = None


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
    icons_url: Optional[str] = None


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
    icons_url: Optional[str] = None
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
