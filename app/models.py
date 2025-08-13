from typing import Optional
from enum import Enum
from datetime import datetime, date
from sqlmodel import SQLModel, Field

class RoleEnum(str, Enum):
    admin = "admin"
    moderator = "moderator"
    user = "user"

class StatusEnum(str, Enum):
    active = "active"
    inactive = "inactive"

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
    dimensions: Optional[str] = None
    diameter: Optional[str] = None
    weight: Optional[str] = None
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
    loan_date: date
    return_date: Optional[date] = None
    returned: bool = False

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
    timeout: int = 500  # ms
    updated_at: datetime = Field(default_factory=datetime.utcnow)
