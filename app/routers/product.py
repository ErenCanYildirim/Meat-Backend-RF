from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.schemas.product import ProductBase, ProductCreate, ProductUpdate, ProductUpdate, ProductResponse
from app.models.product import Product, ProductCategory
from app import crud

from app.config.database import get_db
from app.auth.dependencies import require_admin

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/", response_model=List[ProductResponse])
def get_all_products(
    category: Optional[ProductCategory] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    if category:
        products = crud.product.get_products_by_category(db, category=category)
    else:
        products = crud.product.get_products(db)
    return products

@router.get("/{product_id}", response_model=ProductResponse)
def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    product = crud.product.get_product(db, product_id=product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    return product

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin) 
):
    try:
        return crud.product.create_product(db=db, product=product)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating product: {str(e)}"
        )

@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)  
):
    updated_product = crud.product.update_product(db, product_id=product_id, product_update=product_update)
    if updated_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    return updated_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)  #
):
    success = crud.product.delete_product(db, product_id=product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )