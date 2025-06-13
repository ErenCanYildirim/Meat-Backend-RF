from datetime import datetime
from typing import List, Optional
from uuid import UUID as PyUUID

from pydantic import BaseModel, ConfigDict

from app.models.order import OrderState


class OrderItemBase(BaseModel):
    product_id: int
    quantity: int


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: Optional[dict] = None


class OrderBase(BaseModel):
    pass


class OrderCreate(OrderBase):
    order_items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    state: Optional[OrderState] = None


class OrderResponse(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_email: str
    order_date: datetime
    state: OrderState
    order_items: List[OrderItemResponse] = []
    user: Optional[dict] = None


class OrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_date: datetime
    state: OrderState
    total_items: int


class OrderStateUpdate(BaseModel):
    state: OrderState
