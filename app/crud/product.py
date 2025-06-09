from fastapi import UploadFile
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
from app.core.file_utils import save_product_image, delete_product_image


def get_product(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()


def get_products(db: Session) -> List[Product]:
    return db.query(Product).order_by(desc(Product.id)).all()


def get_products_by_category(db: Session, category: ProductCategory) -> List[Product]:
    return (
        db.query(Product)
        .filter(Product.category == category)
        .order_by(desc(Product.id))
        .all()
    )


def create_product(db: Session, product: ProductCreate) -> Product:
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def create_product_with_image(
    db: Session, product: ProductCreate, image_file: Optional[UploadFile] = None
) -> Product:
    image_link = None

    if image_file:
        image_link = save_product_image(
            file=image_file,
            category=product.category,
            custom_filename=product.description,
        )

    product_data = product.dict()
    product_data["image_link"] = image_link

    db_product = Product(**product_data)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def update_product(
    db: Session, product_id: int, product_update: ProductUpdate
) -> Optional[Product]:
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product:
        update_data = product_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_product, field, value)
        db.commit()
        db.refresh(db_product)
    return db_product


def update_product_with_image(
    db: Session,
    product_id: int,
    product_update: ProductUpdate,
    image_file: Optional[UploadFile] = None,
) -> Optional[Product]:

    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        return None

    if image_file:
        if db_product.image_link:
            delete_product_image(db_product.image_link)

        category = product_update.category or db_product.category
        description = product_update.description or db_product.description

        new_image_link = save_product_image(
            file=image_file, category=category, custom_filename=description
        )

        setattr(db_product, "image_link", new_image_link)

    update_data = product_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)

    db.commit()
    db.refresh(db_product)
    return db_product


def delete_product_with_image(db: Session, product_id: int) -> bool:
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product:
        if db_product.image_link:
            delete_product_image(db_product.image_link)

        db.delete(db_product)
        db.commit()
        return True
    return False


def delete_product(db: Session, product_id: int) -> bool:
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product:
        db.delete(db_product)
        db.commit()
        return True
    return False
