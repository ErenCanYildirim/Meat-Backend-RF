import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException
from app.models.product import ProductCategory


def get_category_folder(category: ProductCategory) -> str:
    """Map ProductCategory to folder name"""
    category_folders = {
        ProductCategory.CHICKEN: "chicken",
        ProductCategory.VEAL: "veal",
        ProductCategory.LAMB: "lamb",
        ProductCategory.BEEF: "beef",
        ProductCategory.OTHER: "other",
    }
    return category_folders.get(category, "other")


def validate_image_file(file: UploadFile) -> None:
    allowed_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}",
        )

    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400, detail="File size too large. Maximum 5MB allowed."
        )


def save_product_image(
    file: UploadFile, category: ProductCategory, custom_filename: Optional[str] = None
) -> str:

    validate_image_file(file)
    category_folder = get_category_folder(category)

    upload_dir = Path(f"app/static/product_images/{category_folder}")
    upload_dir.mkdir(parents=True, exist_ok=True)

    if custom_filename:
        filename = f"{custom_filename}{Path(file.filename).suffix.lower()}"
    else:
        filename = f"{uuid.uuid4()}{Path(file.filename).suffix.lower()}"

    file_path = upload_dir / filename

    try:
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    finally:
        file.file.close()

    return f"/static/product_images/{category_folder}/{filename}"


def delete_product_image(image_path: str) -> bool:
    if not image_path:
        return True

    try:
        file_path = Path(f"app{image_path}")
        if file_path.exists():
            file_path.unlink()
            return True
    except Exception as e:
        print(f"Error deleting image: {e}")
    return False
