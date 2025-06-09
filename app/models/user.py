from sqlalchemy import Column, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from enum import Enum

from .base import Base, TimestampMixin, UUIDMixin

__all__ = ["User", "Role", "UserRoleEnum", "user_roles"]


class UserRoleEnum(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    CUSTOMER = "customer"


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id"), primary_key=True),
    Column("role_id", String, ForeignKey("roles.id"), primary_key=True),
)


class Role(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "roles"

    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(200))

    users = relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self):
        return f"<Role(name='{self.name}')>"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    company_name = Column(String(100), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    # orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', company_name='{self.company_name}', active={self.is_active})>"

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)

    def is_admin(self) -> bool:
        return self.has_role(UserRoleEnum.ADMIN.value)

    def is_manager(self) -> bool:
        return self.has_role(UserRoleEnum.MANAGER.value) or self.is_admin()

    @property
    def role_names(self) -> list[str]:
        return [role.name for role in self.roles]
