from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    UploadFile,
    File,
    Form,
)
from sqlalchemy.orm import Session
from typing import List, Optional

from app.schemas.product import (
    ProductBase,
    ProductCreate,
    ProductUpdate,
    ProductUpdate,
    ProductResponse,
)
from app.models.product import Product, ProductCategory
from app import crud

from app.config.database import get_db
from app.auth.dependencies import require_admin
from app.core.file_utils import save_product_image, delete_product_image

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=List[ProductResponse])
def get_all_products(
    category: Optional[ProductCategory] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
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
            detail=f"Product with id {product_id} not found",
        )
    return product


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_product(
    description: str = Form(..., min_length=1, max_length=100),
    category: ProductCategory = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    try:
        product_data = ProductCreate(description=description, category=category)

        return crud.create_product_with_image(
            db=db, product=product_data, image_file=image
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating product: {str(e)}",
        )


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_admin)],
)
def update_product(
    product_id: int,
    description: Optional[str] = Form(None, min_length=1, max_length=500),
    category: Optional[ProductCategory] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    try:
        product_update = ProductUpdate(description=description, category=category)

        updated_product = crud.update_product_with_image(
            db=db,
            product_id=product_id,
            product_update=product_update,
            image_file=image,
        )

        if updated_product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found",
            )

        return updated_product
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating product: {str(e)}",
        )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    success = crud.delete_product_with_image(db, product_id=product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )


@router.post("/{product_id}/image", dependencies=[Depends(require_admin)])
def upload_product_image(
    product_id: int, image: UploadFile = File(...), db: Session = Depends(get_db)
):
    db_product = crud.get_product(db, product_id=product_id)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )

    try:
        if db_product.image_link:
            delete_product_image(db_product.image_link)

        new_image_link = save_product_image(
            file=image,
            category=db_product.category,
            custom_filename=db_product.description,
        )

        db_product.image_link = new_image_link
        db.commit()
        db.refresh(db_product)

        return {"message": "Image uploaded successfully", "image_link": new_image_link}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error uploading image: {str(e)}",
        )


@router.delete("/{product_id}/image", dependencies=[Depends(require_admin)])
def delete_product_image_only(
    product_id: int,
    db: Session = Depends(get_db),
):
    db_product = crud.get_product(db, product_id=product_id)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )

    if db_product.image_link:
        delete_product_image(db_product.image_link)
        db_product.image_link = None
        db.commit()
        db.refresh(db_product)

    return {"message": "Image deleted successfully"}


"""
@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin())],
)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
):
    try:
        return crud.product.create_product(db=db, product=product)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating product: {str(e)}",
        )


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_admin())],
)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
):
    updated_product = crud.product.update_product(
        db, product_id=product_id, product_update=product_update
    )
    if updated_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )
    return updated_product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin())],
)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    success = crud.product.delete_product(db, product_id=product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )
"""
