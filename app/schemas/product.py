from pydantic import BaseModel, Field
from typing import Optional
from app.models.product import ProductCategory

class ProductBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=100)
    image_link: Optional[str] = None
    category: ProductCategory

class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    image_link: Optional[str] = None
    category: Optional[ProductCategory] = None


class ProductResponse(ProductBase):
    id: int

    class Config:
        from_attributes = True
