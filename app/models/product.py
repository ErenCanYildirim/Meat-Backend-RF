from enum import Enum

from sqlalchemy import Column
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String

from app.models.base import Base


class ProductCategory(str, Enum):
    CHICKEN = "Hähnchen"
    VEAL = "Kalb"
    LAMB = "Lamm"
    BEEF = "Rind"
    OTHER = "Sonstiges"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    image_link = Column(String, nullable=True)
    category = Column(SQLEnum(ProductCategory), nullable=False)
