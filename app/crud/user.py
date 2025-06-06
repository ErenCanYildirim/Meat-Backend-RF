from sqlalchemy.orm import Session
from uuid import uuid4

from app.models.user import User, Role
from app.schemas.user import UserCreate, UserCreateWithRoles, UserUpdate

def get_users(db: Session):
    return db.query(User).all()

def get_user(db: Session, user_id: str):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_company_name(db: Session, company_name: str):
    return db.query(User).filter(User.company_name == company_name).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user_with_hashed_password(db: Session, user: UserCreate):
    from app.auth import get_password_hash
    hashed_password = get_password_hash(user.password)
    db_user = User(
        id=str(uuid4()),
        email=user.email,
        company_name=user.company_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

#potentially irrelevant and unsafe method
def create_user(db: Session, user: UserCreate):
    db_user = User(
        id=str(uuid4()),
        email=user.email,
        hashed_password=user.password,
        company_name = user.company_name,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_user_with_roles(db: Session, user: UserCreateWithRoles):
    db_user = create_user(db, user)
    if user.role_ids:
        roles = db.query(Role).filter(Role.id.in_(user.role_ids)).all()
        db_user.roles = roles
        db.commit()
    return db_user

def update_user(db: Session, user_id: str, user_update: UserUpdate):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None

    update_data = user_update.dict(exclude_unset=True)

    if not update_data:
        return db_user

    for key, value in update_data.items():
        if key == "password" and value is not None:
            db_user.hashed_password = value
        elif key == "role_ids" and value is not None:
            db_user.roles.clear()
            if value:
                roles = db.query(Role).filter(Role.id.in_(value)).all()
                db_user.roles.extend(roles)
        else:
            setattr(db_user, key, value)

    # db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: str):
    
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None 

    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully", "user_id": user_id}