from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta
from uuid import uuid4

from app.config.database import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.auth.core import (
    get_password_hash,
    create_access_token,
    authenticate_user,
    get_current_user,
    COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_DAYS,
)
from app.models.user import User
from app.crud.user import get_user, get_user_by_email, get_user_by_company_name, create_user_with_hashed_password
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=dict)
async def register(user_data: UserCreate, response: Response, db:Session = Depends(get_db)):
    if get_user_by_email(db, user_data.email):
        return {"error": "Email already registered!"}

    if get_user_by_company_name(db, user_data.company_name):
        return {"error": "Company name already taken!"}
    
    db_user = create_user_with_hashed_password(db, user_data)

    access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data = {"sub": db_user.company_name}, expires_delta=access_token_expires
    )

    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure="production",
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_DAYS*24*60*60,
    )

    return {
        "user":{
            "id":db_user.id,
            "email":db_user.email,
            "username":db_user.company_name,
            "created_at":db_user.created_at
        }
    }

@router.post("/login", response_model=dict)
async def login(user_data: UserLogin, response: Response, db:Session = Depends(get_db)):
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        return {"error": "Falscher Nutzername oder Passwort!"}
    
    access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub":user.company_name}, expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure="production",
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_DAYS*24*60*60, 
    )

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.company_name,
            "created_at": user.created_at
        }
    }
    

@router.get("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure="production",
        samesite="lax"
    )
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user:User = Depends(get_current_user)):
    return current_user