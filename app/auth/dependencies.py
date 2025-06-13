from typing import List

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.core import ALGORITHM, COOKIE_NAME, SECRET_KEY
from app.config.database import get_db
from app.models.user import UserRoleEnum


class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, request: Request, db: Session = Depends(get_db)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        insufficient_permissions = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

        token = request.cookies.get(COOKIE_NAME)
        if not token:
            raise credentials_exception

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            company_name: str = payload.get("sub")
            user_roles: List[str] = payload.get("roles", [])

            if company_name is None:
                raise credentials_exception

        except jwt.PyJWTError:
            raise credentials_exception

        if not any(role in user_roles for role in self.allowed_roles):
            raise insufficient_permissions

        return {"company_name": company_name, "roles": user_roles}


def require_admin():
    return RoleChecker([UserRoleEnum.ADMIN.value])


def require_manager():
    return RoleChecker([UserRoleEnum.MANAGER.value, UserRoleEnum.ADMIN.value])


def require_customer():
    return RoleChecker(
        [
            UserRoleEnum.CUSTOMER.value,
            UserRoleEnum.MANAGER.value,
            UserRoleEnum.ADMIN.value,
        ]
    )
