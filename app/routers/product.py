from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app import crud
from app.auth.dependencies import require_admin
from app.config.database import get_db
from app.core.file_utils import (
    ALLOWED_IMAGE_TYPES,
    MAX_DESCRIPTION_LENGTH,
    MAX_IMAGE_SIZE,
    MIN_DESCRIPTION_LENGTH,
    delete_product_image,
    handle_database_error,
    save_product_image,
    validate_image_file,
)
from app.models.product import Product, ProductCategory
from app.schemas.product import (
    ProductBase,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=List[ProductResponse])
async def get_all_products(
    category: Optional[ProductCategory] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
):
    try:
        if category:
            products = crud.product.get_products_by_category(db, category=category)
        else:
            products = crud.product.get_products(db)
        return products
    except Exception as e:
        raise handle_database_error(e, "get_all_products")


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    try:
        product = crud.product.get_product(db, product_id=product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found",
            )
        return product
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error(e, "get_product_by_id")


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_product(
    description: str = Form(..., min_length=1, max_length=100),
    category: ProductCategory = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    if image:
        validate_image_file(image)
    try:
        product_data = ProductCreate(description=description, category=category)

        db.begin()
        try:
            created_product = crud.product.create_product_with_image(
                db=db, product=product_data, image_file=image
            )
            db.commit()
            return created_product
        except Exception as e:
            db.rollback()
            if image and hasattr(e, "image_path"):
                try:
                    delete_product_image(e.image_path)
                except Exception as cleanup_error:
                    print(f"Failed to cleanup image after DB error: {cleanup_error}")
            raise e
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error(e, "creating product")


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_admin)],
)
async def update_product(
    product_id: int,
    description: Optional[str] = Form(
        None, min_length=MIN_DESCRIPTION_LENGTH, max_length=MAX_DESCRIPTION_LENGTH
    ),
    category: Optional[ProductCategory] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Update an existing product."""
    # Validate image if provided
    if image:
        validate_image_file(image)

    try:
        product_update = ProductUpdate(description=description, category=category)

        # Use database transaction
        db.begin()
        old_image_path = None
        new_image_path = None

        try:
            # Get current product to track old image
            existing_product = crud.product.get_product(db, product_id=product_id)
            if not existing_product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {product_id} not found",
                )

            old_image_path = existing_product.image_link

            updated_product = crud.product.update_product_with_image(
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

            new_image_path = updated_product.image_link
            db.commit()

            if old_image_path and old_image_path != new_image_path:
                try:
                    delete_product_image(old_image_path)
                except Exception as cleanup_error:
                    print(
                        f"Failed to delete old image {old_image_path}: {cleanup_error}"
                    )

            return updated_product

        except Exception as e:
            db.rollback()
            if new_image_path and new_image_path != old_image_path:
                try:
                    delete_product_image(new_image_path)
                except Exception as cleanup_error:
                    print(
                        f"Failed to cleanup new image after DB error: {cleanup_error}"
                    )
            raise e

    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error(e, "updating product")


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    try:
        db.begin()
        try:
            success = crud.product.delete_product_with_image(db, product_id=product_id)
            if not success:
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {product_id} not found",
                )
        except Exception as e:
            db.rollback()
            raise e
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error(e, "delete_product")


@router.post("/{product_id}/image", dependencies=[Depends(require_admin)])
async def upload_product_image(
    product_id: int, image: UploadFile = File(...), db: Session = Depends(get_db)
):
    validate_image_file(image)

    try:
        db_product = crud.product.get_product(db, product_id=product_id)

        if not db_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found",
            )

        db.begin()
        old_image_path = db_product.image_link
        new_image_path = None

        try:
            new_image_path = save_product_image(
                file=image,
                category=db_product.category,
                custom_filename=db_product.description,
            )

            db.product.image_link = db_product.image_link
            db.commit()
            db.refresh(db_product)

            if old_image_path:
                try:
                    delete_product_image(old_image_path)
                except Exception as cleanup_error:
                    print(
                        f"Failed to delete old image: {old_image_path}: {cleanup_error}"
                    )
            return {
                "message": "Image successfully uploaded",
                "image_link": new_image_path,
            }

        except Exception as e:
            db.rollback()
            if new_image_path:
                try:
                    delete_product_image(new_image_path)
                except Exception as cleanup_error:
                    print(f"Failed to cleanup image after DB error: {cleanup_error}")
            raise e
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error(e, "upload_product_image")


@router.delete("/{product_id}/image", dependencies=[Depends(require_admin)])
async def delete_product_image_only(
    product_id: int,
    db: Session = Depends(get_db),
):
    try:
        db_product = crud.product.get_product(db, product_id=product_id)
        if not db_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found",
            )

        db.begin()
        old_image_path = db_product.image_link

        try:
            db_product.image_link = None
            db.commit()
            db.refresh(db_product)

            if old_image_path:
                try:
                    delete_product_image(old_image_path)
                except Exception as cleanup_error:
                    print(
                        f"Failed to delete image file {old_image_path} : {cleanup_error}"
                    )
            return {"message": "Image deleted successfully"}

        except Exception as e:
            db.rollback()
            raise e
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error(e, "delete_product_image")
