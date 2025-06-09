from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    ForeignKey,
    Text,
    Enum,
    DateTime,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.config.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token = Column(String, primary_key=True, index=True)
    email = Column(String, index=True)
    expires_at = Column(DateTime)
    used = Column(Boolean, default=False)
