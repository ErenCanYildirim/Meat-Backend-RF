from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID as PyUUID

from sqlalchemy import UUID, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class OrderState(str, Enum):
    ORDER_PLACED = "order_placed"
    INVOICE_GENERATED = "invoice_generated"
    EMAIL_SENT = "email_sent"
    PDF_FAILED = "pdf_failed"
    EMAIL_FAILED = "email_failed"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("users.email"), nullable=False)
    order_date = Column(DateTime, default=func.now(), nullable=False)
    state = Column(SQLEnum(OrderState), default=OrderState.ORDER_PLACED, nullable=False)

    user = relationship("User", back_populates="orders")
    order_items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="order_items")
    product = relationship("Product")
