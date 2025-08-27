# Plik: app/models.py (cała, zaktualizowana zawartość)

from typing import Optional
from enum import Enum
from datetime import datetime, date
from sqlmodel import SQLModel, Field, Column, JSON
import uuid

# --- Enumy bez zmian ---
class RoleEnum(str, Enum):
    admin = "admin"
    moderator = "moderator"
    user = "user"

class StatusEnum(str, Enum):
    active = "active"
    inactive = "inactive"

# --- Modele z bazą danych ---

class User(SQLModel, table=True):
    id: str = Field(primary_key=True)
    first_name: str
    last_name: str
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: RoleEnum = Field(default=RoleEnum.user)
    status: StatusEnum = Field(default=StatusEnum.active)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

class Tool(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    quantity_total: int = Field(default=1, description="Całkowita liczba posiadanych sztuk")
    quantity_available: int = Field(default=1, description="Liczba sztuk aktualnie dostępnych")

    # --- ZMIANA: Precyzyjna waga ---
    weight_value: Optional[float] = Field(default=None, description="Wartość wagi")
    weight_unit: str = Field(default="g", description="Jednostka wagi (g, kg)")
    # --------------------------------

    # --- ZMIANA: Precyzyjne wymiary ---
    width: Optional[float] = Field(default=None, description="Szerokość w mm")
    height: Optional[float] = Field(default=None, description="Wysokość w mm")
    area: Optional[float] = Field(default=None, description="Pole powierzchni w mm^2 (obliczane zewnętrznie)")
    # -----------------------------------

    # --- USUNIĘTE POLA ---
    # dimensions: Optional[str] = None
    # weight: Optional[str] = None
    # ---------------------

    diameter: Optional[str] = None # To pole zostaje, może być przydatne dla wierteł itp.
    type: Optional[str] = None
    status: Optional[str] = None
    condition: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ToolLoan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool_id: int = Field(foreign_key="tool.id")
    user_id: str = Field(foreign_key="user.id")
    # --- ZMIANA Z DATE NA DATETIME ---
    loan_date: datetime = Field(default_factory=datetime.utcnow)
    return_date: Optional[datetime] = None
    # ----------------------------------
    returned: bool = False

# --- Pozostałe modele bez zmian ---
class ToolWeight(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool_id: int = Field(foreign_key="tool.id")
    weight_value: float
    measured_at: datetime = Field(default_factory=datetime.utcnow)
    measured_by: Optional[str] = Field(default=None, foreign_key="user.id")

class ScaleConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    port: str = "/dev/ttyUSB0"
    baudrate: int = 9600
    parity: str = "N"
    data_bits: int = 8
    stop_bits: int = 1
    timeout: int = 500
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    session_token: str = Field(index=True)
    is_active: bool = Field(default=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ... (reszta modeli, które dodałeś wcześniej, bez zmian)
class UserPermission(SQLModel, table=True):
    __tablename__ = "user_permissions"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    module: str
    permission: str
    granted: bool = Field(default=True)

class ExternalIntegration(SQLModel, table=True):
    __tablename__ = "external_integrations"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    type: str
    config: dict = Field(default={}, sa_column=Column(JSON))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class IntegrationLog(SQLModel, table=True):
    __tablename__ = "integration_logs"
    id: Optional[int] = Field(default=None, primary_key=True)
    integration_id: str = Field(foreign_key="external_integrations.id")
    event_type: str
    message: Optional[str] = None
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class WarehouseConfig(SQLModel, table=True):
    __tablename__ = "warehouse_config"
    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str
    options: dict = Field(default={}, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ToolOrder(SQLModel, table=True):
    __tablename__ = "tool_orders"
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: Optional[str] = Field(default=None, index=True)
    items: list = Field(default=[], sa_column=Column(JSON))
    status: str = Field(default="pending")
    ordered_at: datetime = Field(default_factory=datetime.utcnow)

class ToolMapping(SQLModel, table=True):
    __tablename__ = "tool_id_mapping"
    id: Optional[int] = Field(default=None, primary_key=True)
    external_tool_id: str = Field(unique=True)
    internal_tool_id: int = Field(foreign_key="tool.id")
