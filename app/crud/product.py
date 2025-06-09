from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from app.models.product import Product, ProductCategory
from app.schemas.product import (
    ProductBase,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)

def get_product(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()

def get_products(db: Session) -> List[Product]:
    return db.query(Product).order_by(desc(Product.id)).all()

def get_products_by_category(db: Session, category: ProductCategory) -> List[Product]:
    return db.query(Product).filter(Product.category == category).order_by(desc(Product.id)).all()

def create_product(db: Session, product: ProductCreate) -> Product:
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product_update: ProductUpdate) -> Optional[Product]:
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product:
        update_data = product_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_product, field, value)
        db.commit()
        db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int) -> bool:
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product:
        db.delete(db_product)
        db.commit()
        return True
    return False

