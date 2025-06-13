from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import Role, User, UserRoleEnum


def get_role_by_name(db: Session, role_name: str) -> Role:
    return db.query(Role).filter(Role.name == role_name).first()


def create_role(db: Session, role_name: str, description: str = "") -> Role:
    db_role = Role(id=str(uuid4()), name=role_name, description=description)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


def get_or_create_role(db: Session, role_name: str, description: str = "") -> Role:
    role = get_role_by_name(db, role_name)
    if not role:
        role = create_role(db, role_name, description)
    return role


def assign_role_to_user(db: Session, user: User, role_name: str):
    role = get_role_by_name(db, role_name)
    if role and role not in user.roles:
        user.roles.append(role)
        db.commit()
        db.refresh(user)


def assign_default_customer_role(db: Session, user: User):
    customer_role = get_or_create_role(
        db, UserRoleEnum.CUSTOMER.value, "Standard customer access"
    )
    if customer_role not in user.roles:
        user.roles.append(customer_role)
        db.commit()
        db.refresh(user)


def initialize_default_roles(db: Session):
    """Create default roles if they don't exist"""
    roles_to_create = [
        (UserRoleEnum.ADMIN.value, "Administrator with full access"),
        (UserRoleEnum.MANAGER.value, "Manager with elevated permissions"),
        (UserRoleEnum.CUSTOMER.value, "Standard customer access"),
    ]

    for role_name, description in roles_to_create:
        get_or_create_role(db, role_name, description)

    print("Default roles initialized successfully")


def count_admin_users(db: Session) -> int:
    admin_count = (
        db.query(func.count(User.id))
        .join(User.roles)
        .filter(Role.name == "admin")
        .scalar()
    )
    return admin_count or 0
