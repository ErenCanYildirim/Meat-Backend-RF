from datetime import date
from typing import List

from pydantic import BaseModel, EmailStr


class ProductQuantityOut(BaseModel):
    product_id: int
    total_kg: float


class AverageQuantityOut(BaseModel):
    average_quantity: float


class ProductOrderFrequencyOut(BaseModel):
    product_id: int
    times_ordered: int


class CustomerQuantityOut(BaseModel):
    user_email: EmailStr
    total_kg: float


class CustomerOrderFrequencyOut(BaseModel):
    user_email: str
    order_count: int


class OrderTimeDistributionOut(BaseModel):
    date: date
    order_count: int
