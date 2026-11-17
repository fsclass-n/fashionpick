from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, field_validator

from .security import validate_password

UTCDateTime = Annotated[
    datetime,
    PlainSerializer(lambda d: d.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"), return_type=str),
]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth / User ----------
class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=50)
    password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        validate_password(v)
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TestLoginIn(BaseModel):
    role: Literal["user", "admin"]


class UserOut(ORM):
    id: int
    email: str
    name: str
    role: str
    provider: str
    is_active: bool
    created_at: UTCDateTime
    last_login_at: UTCDateTime | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RoleIn(BaseModel):
    role: Literal["user", "admin"]


# ---------- Supplier ----------
class SupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    contact_name: str = ""
    phone: str = ""
    email: EmailStr | Literal[""] = ""
    webhook_url: str = ""
    order_method: Literal["email", "webhook", "manual"] = "email"
    template: Literal["standard", "simple"] = "standard"
    address: str = ""
    memo: str = ""


class SupplierOut(ORM, SupplierIn):
    id: int
    email: str = ""
    created_at: UTCDateTime


# ---------- Product ----------
class ProductOut(ORM):
    id: int
    supplier_id: int
    supplier_name: str = ""
    name: str
    category: str
    keyword: str
    wholesale_price: int
    sale_price: int
    margin_rate: float = 0
    image_url: str
    image_ratio: float
    source_url: str
    options: dict
    stock: int
    status: str
    registered_name: str | None = None
    sourced_at: UTCDateTime
    registered_at: UTCDateTime | None = None


class ProductRegisterIn(BaseModel):
    registered_name: str | None = Field(default=None, max_length=255)
    sale_price: int | None = Field(default=None, gt=0)


# ---------- Order ----------
class OrderItemIn(BaseModel):
    product_id: int
    option: str = ""
    quantity: int = Field(ge=1, le=999)


class OrderIn(BaseModel):
    customer_name: str = Field(min_length=1, max_length=100)
    customer_phone: str = ""
    address: str = ""
    channel: str = "fashionpick"
    items: list[OrderItemIn] = Field(min_length=1)


class OrderItemOut(ORM):
    id: int
    product_id: int
    product_name: str
    option: str
    quantity: int
    unit_price: int
    wholesale_price: int
    purchase_order_id: int | None = None


class OrderOut(ORM):
    id: int
    order_no: str
    customer_name: str
    customer_phone: str
    address: str
    channel: str
    status: str
    total_amount: int
    created_at: UTCDateTime
    items: list[OrderItemOut]


class PurchaseOrderOut(ORM):
    id: int
    po_no: str
    supplier_id: int
    supplier_name: str = ""
    supplier_method: str = ""
    status: str
    total_amount: int
    send_channel: str
    send_log: str
    created_at: UTCDateTime
    sent_at: UTCDateTime | None = None
    received_at: UTCDateTime | None = None
    items: list[OrderItemOut] = []


class PurchaseOrderStatusIn(BaseModel):
    status: Literal["pending", "sent", "received"]


# ---------- RPA ----------
class RpaJobOut(ORM):
    id: int
    name: str
    label: str
    interval_minutes: int
    enabled: bool
    last_run_at: UTCDateTime | None = None
    last_status: str


class RpaJobUpdateIn(BaseModel):
    interval_minutes: int | None = Field(default=None, ge=5, le=10080)
    enabled: bool | None = None


class RpaLogOut(ORM):
    id: int
    job_name: str
    status: str
    triggered_by: str
    items_count: int
    message: str
    started_at: UTCDateTime
    finished_at: UTCDateTime | None = None
