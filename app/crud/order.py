from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderItem, OrderState
from app.schemas.order import (FailureOrdersRequest, FailureType, OrderCreate,
                               OrderUpdate)


def get_all_orders(db: Session, skip: int = 0, limit: int = 50) -> List[Order]:
    orders = db.query(Order).offset(skip).limit(limit).all()
    return orders


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


def get_failed_orders(
    db: Session, failure_type: str = "all", skip: int = 0, limit: int = 100
) -> List[Order]:
    query = db.query(Order)

    if failure_type.lower() == "pdf":
        query = query.filter(Order.state == OrderState.PDF_FAILED)
    elif failure_type.lower() == "email":
        query = query.filter(Order.state == OrderState.EMAIL_FAILED)
    elif failure_type.lower() == "all":
        query = query.filter(
            or_(
                Order.state == OrderState.PDF_FAILED,
                Order.state == OrderState.EMAIL_FAILED,
            )
        )
    else:
        return []

    orders = query.order_by(Order.order_date.desc()).offset(skip).limit(limit).all()

    return orders if orders is not None else []


def get_failed_orders_count(db: Session) -> Dict[str, int]:
    pdf_failed_count = (
        db.query(Order).filter(Order.state == OrderState.PDF_FAILED).count()
    )
    email_failed_count = (
        db.query(Order).filter(Order.state == OrderState.EMAIL_FAILED).count()
    )
    total_failed_count = pdf_failed_count + email_failed_count

    return {
        "total_failed": total_failed_count,
        "pdf_failed": pdf_failed_count,
        "email_failed": email_failed_count,
    }
