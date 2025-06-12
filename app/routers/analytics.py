from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import List

from app.config.database import get_db
from app.crud import analytics as analytics_crud
from app.auth.dependencies import require_admin

from app.schemas.analytics import (
    ProductQuantityOut,
    AverageQuantityOut,
    ProductOrderFrequencyOut,
    CustomerQuantityOut,
    CustomerOrderFrequencyOut,
    OrderTimeDistributionOut,
)


router = APIRouter(prefix="/analytics", tags=["Analytics"])

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


@router.get(
    "/total_quantity_per_product",
    response_model=List[ProductQuantityOut],
    dependencies=[Depends(require_admin())],
)
async def get_total_quantity_per_product(db: Session = Depends(get_db)):
    result = analytics_crud.get_total_quantity_per_product(db)
    return [
        ProductQuantityOut(product_id=product_id, total_kg=float(total_kg))
        for product_id, total_kg in result
    ]


@router.get(
    "/average_quantity_per_order",
    response_model=AverageQuantityOut,
    dependencies=[Depends(require_admin())],
)
async def get_average_quantity_per_order(db: Session = Depends(get_db)):
    result = analytics_crud.get_average_quantity_per_order(db)
    return AverageQuantityOut(average_quantity=float(result))


@router.get(
    "/most_ordered_products",
    response_model=List[ProductQuantityOut],
    dependencies=[Depends(require_admin())],
)
async def get_most_ordered_products(db: Session = Depends(get_db)):
    result = analytics_crud.get_most_ordered_products(db)
    return [
        ProductQuantityOut(product_id=product_id, total_kg=float(total_kg))
        for product_id, total_kg in result
    ]


@router.get(
    "/least_ordered_products",
    response_model=List[ProductQuantityOut],
    dependencies=[Depends(require_admin())],
)
async def get_least_ordered_products(db: Session = Depends(get_db)):
    result = analytics_crud.get_least_ordered_products(db)
    return [
        ProductQuantityOut(product_id=product_id, total_kg=float(total_kg))
        for product_id, total_kg in result
    ]


@router.get(
    "/product_order_frequency",
    response_model=List[ProductOrderFrequencyOut],
    dependencies=[Depends(require_admin())],
)
async def get_product_order_frequency(db: Session = Depends(get_db)):
    result = analytics_crud.get_product_order_frequency(db)
    return [
        ProductOrderFrequencyOut(product_id=product_id, times_ordered=times_ordered)
        for product_id, times_ordered in result
    ]


@router.get(
    "/top_customers_by_quantity",
    response_model=List[CustomerQuantityOut],
    dependencies=[Depends(require_admin())],
)
async def get_top_customers_by_quantity(db: Session = Depends(get_db)):
    result = analytics_crud.get_top_customers_by_quantity(db)
    return [
        CustomerQuantityOut(user_email=user_email, total_kg=float(total_kg))
        for user_email, total_kg in result
    ]


@router.get(
    "/customer_order_frequency",
    response_model=List[CustomerOrderFrequencyOut],
    dependencies=[Depends(require_admin())],
)
async def get_customer_order_frequency(db: Session = Depends(get_db)):
    result = analytics_crud.get_customer_order_frequency(db)
    return [
        CustomerOrderFrequencyOut(user_email=user_email, order_count=order_count)
        for user_email, order_count in result
    ]


@router.get(
    "/order_time_distribution",
    response_model=List[OrderTimeDistributionOut],
    dependencies=[Depends(require_admin())],
)
async def get_order_time_distribution(db: Session = Depends(get_db)):
    result = analytics_crud.get_order_time_distribution(db)
    return [
        OrderTimeDistributionOut(date=date, order_count=order_count)
        for date, order_count in result
    ]
