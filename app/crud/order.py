from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status

from app.models.order import Order, OrderItem, OrderState
from app.schemas.order import OrderCreate, OrderUpdate


def get_orders_by_user_email(
    db: Session, user_email: str, skip: int = 0, limit: int = 10
) -> List[Order]:

    orders = (
        db.query(Order)
        .options(
            joinedload(Order.order_items).joinedload(OrderItem.product),
            joinedload(Order.user),
        )
        .filter(Order.user_email == user_email)
        .order_by(Order.order_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return orders if orders is not None else []


def get_orders_by_date(
    db: Session, order_date: date, skip: int = 0, limit: int = 10
) -> List[Order]:

    start_of_day = datetime.combine(order_date, datetime.min.time())
    end_of_day = datetime.combine(order_date, datetime.max.time())

    orders = (
        db.query(Order)
        .options(
            joinedload(Order.order_items).joinedload(OrderItem.product),
            joinedload(Order.user),
        )
        .filter(and_(Order.order_date >= start_of_day, Order.order_date <= end_of_day))
        .order_by(Order.order_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return orders if orders is not None else []


def get_order_by_id(db: Session, order_id: int) -> Optional[Order]:

    order = (
        db.query(Order)
        .options(
            joinedload(Order.order_items).joinedload(OrderItem.product),
            joinedload(Order.user),
        )
        .filter(Order.id == order_id)
        .first()
    )
    return order if order is not None else []


def create_order(db: Session, order: OrderCreate, user_email: str) -> Order:
    db_order = Order(user_email=user_email, state=OrderState.ORDER_PLACED)
    db.add(db_order)
    db.flush()

    for item in order.order_items:
        db_item = OrderItem(
            order_id=db_order.id, product_id=item.product_id, quantity=item.quantity
        )
        db.add(db_item)

    db.commit()
    db.refresh(db_order)

    return get_order_by_id(db, db_order.id)


def update_order_state(
    db: Session, order_id: int, new_state: OrderState
) -> Optional[Order]:
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        return None

    db_order.state = new_state
    db.commit()
    db.refresh(db_order)

    return get_order_by_id(db, order_id)
