from datetime import date, datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from rq import Queue, Retry, Worker
from rq.job import Job
from sqlalchemy.orm import Session

from app.auth.core import get_current_user
from app.auth.dependencies import require_admin
from app.config.database import get_db
from app.config.redis_config import get_pdf_queue, move_to_dead_letter_queue
from app.crud import order as order_crud
from app.middleware.prometheus_middleware import record_order_created
from app.models.order import OrderState
from app.schemas.order import (FailureType, OrderCreate, OrderResponse,
                               OrderStateUpdate)
from app.services.tasks import generate_pdf_task

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get(
    "/",
    response_model=List[OrderResponse],
    dependencies=[Depends(require_admin())],
)
async def get_all_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    orders = order_crud.get_all_orders(db=db, skip=skip, limit=limit)

    if not orders:
        return []

    response_orders = []
    for order in orders:
        response_orders.append(
            {
                "id": order.id,
                "user_email": order.user_email,
                "order_date": order.order_date,
                "state": order.state,
                "order_items": [
                    {
                        "id": item.id,
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "product": (
                            {
                                "id": item.product.id,
                                "description": item.product.description,
                                "image_link": item.product.image_link,
                                "category": item.product.category,
                            }
                            if item.product
                            else None
                        ),
                    }
                    for item in order.order_items
                ],
                "user": (
                    {"email": order.user.email, "company_name": order.user.company_name}
                    if order.user
                    else None
                ),
            }
        )
    return response_orders


@router.get(
    "/user/{user_email}",
    response_model=List[OrderResponse],
    dependencies=[Depends(require_admin())],
)
async def get_orders_by_email(
    user_email: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    orders = order_crud.get_orders_by_user_email(
        db=db, user_email=user_email, skip=skip, limit=limit
    )

    if not orders:
        return []

    response_orders = []
    for order in orders:
        response_orders.append(
            {
                "id": order.id,
                "user_email": order.user_email,
                "order_date": order.order_date,
                "state": order.state,
                "order_items": [
                    {
                        "id": item.id,
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "product": (
                            {
                                "id": item.product.id,
                                "description": item.product.description,
                                "image_link": item.product.image_link,
                                "category": item.product.category,
                            }
                            if item.product
                            else None
                        ),
                    }
                    for item in order.order_items
                ],
                "user": (
                    {"email": order.user.email, "company_name": order.user.company_name}
                    if order.user
                    else None
                ),
            }
        )
    return response_orders


@router.get("/my-orders", response_model=List[OrderResponse])
async def get_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    orders = order_crud.get_orders_by_user_email(
        db=db, user_email=current_user.email, skip=skip, limit=limit
    )

    if not orders:
        return []

    response_orders = []
    for order in orders:
        response_orders.append(
            {
                "id": order.id,
                "user_email": order.user_email,
                "order_date": order.order_date,
                "state": order.state,
                "order_items": [
                    {
                        "id": item.id,
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "product": (
                            {
                                "id": item.product.id,
                                "description": item.product.description,
                                "image_link": item.product.image_link,
                                "category": item.product.category,
                            }
                            if item.product
                            else None
                        ),
                    }
                    for item in order.order_items
                ],
                "user": (
                    {"email": order.user.email, "company_name": order.user.company_name}
                    if order.user
                    else None
                ),
            }
        )
    return response_orders


@router.get(
    "/date/{order_date}",
    response_model=List[OrderResponse],
    dependencies=[Depends(require_admin())],
)
async def get_orders_by_date(
    order_date: date,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    orders = order_crud.get_orders_by_date(
        db=db, order_date=order_date, skip=skip, limit=limit
    )

    if not orders:
        return []

    response_orders = []
    for order in orders:
        response_orders.append(
            {
                "id": order.id,
                "user_email": order.user_email,
                "order_date": order.order_date,
                "state": order.state,
                "order_items": [
                    {
                        "id": item.id,
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "product": (
                            {
                                "id": item.product.id,
                                "description": item.product.description,
                                "image_link": item.product.image_link,
                                "category": item.product.category,
                            }
                            if item.product
                            else None
                        ),
                    }
                    for item in order.order_items
                ],
                "user": (
                    {"email": order.user.email, "company_name": order.user.company_name}
                    if order.user
                    else None
                ),
            }
        )

    return response_orders


@router.get("/{order_id}/status", dependencies=[Depends(require_admin())])
async def get_order_status(
    order_id: int,
    db: Session = Depends(get_db),
    dependencies=[Depends(require_admin())],
):
    order = order_crud.get_order_by_id(db=db, order_id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    return {"order_id": order.id, "state": order.state, "order_date": order.order_date}


@router.post("/place-order", response_model=OrderResponse)
async def place_order(
    order: OrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        db_order = order_crud.create_order(
            db=db, order=order, user_email=current_user.email
        )

        order_data = {
            "order_id": db_order.id,
            "user_email": db_order.user_email,
            "order_date": (
                db_order.order_date.isoformat() if db_order.order_date else None
            ),
            "state": db_order.state,
            "customer_name": db_order.user.company_name if db_order.user else "Unknown",
            "customer_email": db_order.user_email,
            "order_items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "product_description": (
                        item.product.description if item.product else "Unknown Product"
                    ),
                    "product_category": (
                        item.product.category if item.product else "Unknown Category"
                    ),
                }
                for item in db_order.order_items
            ],
        }

        print(f"New order created in database: {db_order.id}")

        pdf_queue = get_pdf_queue()
        pdf_job = pdf_queue.enqueue(
            generate_pdf_task,
            order_data=order_data,
            job_timeout=600,
            retry=Retry(max=3, interval=[60, 120, 240]),
            failure_ttl=3600,
            on_failure=move_to_dead_letter_queue,
        )

        print(f"PDF generation task queued with job ID: {pdf_job.id}")

        response_data = {
            "id": db_order.id,
            "user_email": db_order.user_email,
            "order_date": db_order.order_date,
            "state": db_order.state,
            "order_items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "product": (
                        {
                            "id": item.product.id,
                            "description": item.product.description,
                            "image_link": item.product.image_link,
                            "category": item.product.category,
                        }
                        if item.product
                        else None
                    ),
                }
                for item in db_order.order_items
            ],
            "user": (
                {
                    "email": db_order.user.email,
                    "company_name": db_order.user.company_name,
                }
                if db_order.user
                else None
            ),
            "queue_info": {
                "pdf_job_id": pdf_job.id,
                "message": "PDF generation and email sending have been queued.",
            },
        }

        record_order_created()  # Prometheus metrics

        return response_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create order: {str(e)}",
        )


@router.patch("/{order_id}/state", dependencies=[Depends(require_admin())])
async def update_order_state(
    order_id: int, state_update: OrderStateUpdate, db: Session = Depends(get_db)
):
    updated_order = order_crud.update_order_state(
        db=db, order_id=order_id, new_state=state_update.state
    )

    if not updated_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    return {
        "order_id": updated_order.id,
        "state": updated_order.state,
        "message": f"Order state updated to {updated_order.state}",
    }


@router.get(
    "/failed",
    response_model=List[OrderResponse],
    dependencies=[Depends(require_admin())],
)
def get_failed_orders(
    failure_type: FailureType = Query(
        FailureType.ALL,
        description="Type of failure to filter by: 'all', 'pdf', or 'email'",
    ),
    skip: int = Query(0, ge=0, description="Number of orders to skip"),
    limit: int = Query(
        100, ge=1, le=100, description="Maximum number of orders to return"
    ),
    db: Session = Depends(get_db),
):
    try:
        orders = order_crud.get_failed_orders(
            db=db, failure_type=failure_type.value, skip=skip, limit=limit
        )
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving failed orders: {str(e)}",
        )


@router.get("/failed/stats", dependencies=[Depends(require_admin())])
def get_failed_orders_stats(db: Session = Depends(get_db)):
    try:
        stats = order_crud.get_failed_orders_count(db=db)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving failed orders statistics: {str(e)}",
        )
