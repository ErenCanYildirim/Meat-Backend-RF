from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import List

from app.config.database import get_db
from app.auth.core import get_current_user
from app.crud import order as order_crud
from app.schemas.order import OrderCreate, OrderResponse, OrderStateUpdate
from app.models.order import OrderState

from app.auth.dependencies import require_admin

router = APIRouter(prefix="/orders", tags=["Orders"])


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

        return {
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
        }

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
