from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, String
from datetime import datetime
import uuid 

Base = declarative_base()

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class UUIDMixin:
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)