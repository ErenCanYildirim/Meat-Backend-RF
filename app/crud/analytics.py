from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, asc, desc, func
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderItem, OrderState
from app.schemas.order import OrderCreate, OrderUpdate

"""
endpoints:
    - total quantity per product
    - avg. quantity per product
    - most ordered product
    - least ordered product
    - product order frequency
    - top_customers_by_quantity
    - customer_order_frequency
    - order_time_distribution
"""


def get_total_quantity_per_product(db: Session):
    return (
        db.query(OrderItem.product_id, func.sum(OrderItem.quantity).label("total_kg"))
        .group_by(OrderItem.product_id)
        .order_by(desc("total_kg"))
        .all()
    )


def get_average_quantity_per_order(db: Session):
    total_quantity = db.query(func.sum(OrderItem.quantity)).scalar()
    total_orders = db.query(func.count(Order.id)).scalar()
    return total_quantity / total_orders if total_orders else 0


def get_most_ordered_products(db: Session, limit=10):
    return (
        db.query(OrderItem.product_id, func.sum(OrderItem.quantity).label("total_kg"))
        .group_by(OrderItem.product_id)
        .order_by(desc("total_kg"))
        .limit(limit)
        .all()
    )


def get_least_ordered_products(db: Session, limit=10):
    return (
        db.query(OrderItem.product_id, func.sum(OrderItem.quantity).label("total_kg"))
        .group_by(OrderItem.product_id)
        .order_by(asc("total_kg"))
        .limit(limit)
        .all()
    )


def get_product_order_frequency(db: Session):
    return (
        db.query(OrderItem.product_id, func.count(OrderItem.id).label("times_ordered"))
        .group_by(OrderItem.product_id)
        .order_by(desc("times_ordered"))
        .all()
    )


def get_top_customers_by_quantity(db: Session, limit=10):
    return (
        db.query(Order.user_email, func.sum(OrderItem.quantity).label("total_kg"))
        .join(OrderItem, Order.id == OrderItem.order_id)
        .group_by(Order.user_email)
        .order_by(desc("total_kg"))
        .limit(limit)
        .all()
    )


def get_customer_order_frequency(db: Session):
    return (
        db.query(Order.user_email, func.count(Order.id).label("order_count"))
        .group_by(Order.user_email)
        .order_by(desc("order_count"))
        .all()
    )


# time distribution per day
def get_order_time_distribution(db: Session):
    return (
        db.query(func.date(Order.order_date).label("date"), func.count(Order.id))
        .group_by(func.date(Order.order_date))
        .order_by(func.date(Order.order_date))
        .all()
    )
