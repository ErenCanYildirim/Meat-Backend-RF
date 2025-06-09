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
from app.crud.user import (
    get_user,
    get_user_by_email,
    get_user_by_company_name,
    create_user_with_hashed_password,
)

from app.models.password_reset import PasswordResetToken
from app.schemas.password import ForgotPasswordRequest, ResetPasswordRequest
from app.auth.pw_reset import generate_reset_token, hash_password, verify_password

from app.crud.roles import assign_default_customer_role

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=dict)
async def register(
    user_data: UserCreate, response: Response, db: Session = Depends(get_db)
):
    if get_user_by_email(db, user_data.email):
        return {"error": "Email already registered!"}

    if get_user_by_company_name(db, user_data.company_name):
        return {"error": "Company name already taken!"}

    db_user = create_user_with_hashed_password(db, user_data)

    assign_default_customer_role(db, db_user)

    # addition of roles to token
    user_roles = [role.name for role in db_user.roles]
    access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": db_user.company_name, "roles": user_roles},
        expires_delta=access_token_expires,
    )

    access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": db_user.company_name}, expires_delta=access_token_expires
    )

    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_DAYS * 3600,
    )

    return {
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "username": db_user.company_name,
            "created_at": db_user.created_at,
            "roles": user_roles,
        }
    }


@router.post("/login", response_model=dict)
async def login(
    user_data: UserLogin, response: Response, db: Session = Depends(get_db)
):
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        return {"error": "Falscher Nutzername oder Passwort!"}

    user_roles = [role.name for role in user.roles]

    access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": user.company_name, "roles": user_roles},
        expires_delta=access_token_expires,
    )

    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_DAYS * 3600,
    )

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.company_name,
            "created_at": user.created_at,
            "roles": user_roles,
        }
    }


@router.get("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, httponly=True, secure=False, samesite="lax")
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


# ---- Forgot Password --------


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest, db: Session = Depends(get_db)
):

    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        return {"message": "If the email exists, a reset link has been sent."}

    token = generate_reset_token()
    expires_at = datetime.utcnow() + timedelta(hours=1)

    db.query(PasswordResetToken).filter(
        PasswordResetToken.email == request.email
    ).delete()

    reset_token = PasswordResetToken(
        token=token, email=request.email, expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()

    email_sent = ""
    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to sent email!")
    return {"message": "If the email exits, a reset link has been sent!"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):

    token_record = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == request.token, PasswordResetToken.used == False
        )
        .first()
    )

    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid or expired token!")

    if datetime.utcnow() > token_record.expires_at:
        raise HTTPException(status_code=400, detail="Token has expired!")

    user = db.query(User).filter(User.email == token_record.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(request.new_password)

    token_record.used = True
    db.commit()

    return {"message": "Password succesfully reset"}
