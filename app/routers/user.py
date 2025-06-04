from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.config.database import get_db
from app import crud
from app.schemas.user import UserRead, UserCreateWithRoles, UserUpdate, UserCreate
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])

#User endpoints

@router.get("/", response_model=List[UserRead])
def list_users(db: Session = Depends(get_db)):
    return crud.user.get_users(db)

@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = crud.user.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/", response_model=UserRead)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    return crud.user.create_user_with_hashed_password(db, user)

@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: str, user_update: UserUpdate, db: Session = Depends(get_db)):
    db_user = crud.user.update_user(db, user_id, user_update)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, db: Session = Depends(get_db)):
    """
    Delete a user by their ID.
    """
    deleted_result = crud.user.delete_user(db, user_id)
    if not deleted_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # For 204 No Content, FastAPI automatically returns nothing.