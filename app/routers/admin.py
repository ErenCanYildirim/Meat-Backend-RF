from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import require_admin, require_manager, require_customer
from app.auth.core import get_current_user
from app.schemas.admin import ( ChangeUserRoleRequest, 
                                ChangePasswordRequest, 
                                ChangeCompanyNameRequest, 
                                ChangeUserEmailRequest)
from app.config.database import get_db
from sqlalchemy.orm import Session
from app.crud.user import get_user_by_email
from app.auth.core import get_password_hash

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/dashboard", dependencies=[Depends(require_admin())])
async def admin_dashboard():
    return {"message": "Welcome to admin dashboard"}

@router.get("/me")
async def get_my_profile(current_user = Depends(get_current_user)):
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "company_name": current_user.company_name,
            "roles": [role.name for role in current_user.roles],
            "is_admin": current_user.is_admin(),
        }
    }

@router.put("/change-user-role")
async def change_user_role(
    role_change: ChangeUserRoleRequest,
    db: Session = Depends(get_db),
    current_user_data: dict = Depends(require_admin())
):
    user = get_user_by_email(db, role_change.user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail = "User not found"
        )
    
    current_user_id = current_user_data.get("user_id")
    if user.id == current_user_id:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail = "Cannot change your own roles"
        )

    new_role = get_role_by_name(db, role_change.new_role)
    if not new_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_change.new_role}' not found"
        )

    if role_change.remove_existing_roles:
        current_admin_roles = [role for role in user.roles if role.name == "admin"]
        if current_admin_roles and new_role.name != "admin":
            from app.crud.admin import count_admin_users
            admin_count = count_admin_users(db)
            if admin_count <= 1:
                raise HTTPException(
                    status_code = status.HTTP_403_FORBIDDEN,
                    detail = "Cannot remove admin privileges from the last admin user"
                )

    if role_change.remove_existing_roles:
        user.roles.clear()
        db.commit()

    if new_role not in user.roles:
        user.roles.append(new_role)
        db.commit()
        db.refresh(user)
    
    return {
        "message": f"Role changed successfully for {role_change.user_email}",
        "user": {
            "email": user.email,
            "company_name": user.company_name,
            "roles": [role.name for role in user.roles]
        }
    }

@router.delete("/remove-user-role")
async def remove_user_role(
    role_removal: ChangeUserRoleRequest,
    db: Session = Depends(get_db),
    current_user_data: dict = Depends(require_admin())
):
    
    user = get_user_by_email(db, role_removal.user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail = "User not found"
        )

    current_user_id = current_user_data.get("user_id")
    if user.id == current_user_id:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Cannot remove roles from yourself"
        )

    role_to_remove = get_role_by_name(db, role_removal.role_name)
    if not role_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_removal.role_name}' not found"
        )

    if role_to_remove.name == "admin":
        from app.crud.admin import count_admin_users
        admin_count = count_admin_users(db)
        if admin_count <= 1:
            raise HTTPException(
                status_code = status.HTTP_403_FORBIDDEN,
                detail = "Cannot remove admin role from the last admin user"
            )

    if role_to_remove in user.roles:
        user.roles.remove(role_to_remove)
        db.commit()
        db.refresh(user)
        message = f"Role '{role_removal.role_name}' removed from {role_removal.user_email}"
    else:
        message = f"User {role_removal.user_email} doesn't have role '{role_removal.role_name}'"
    
    return {
        "message": message,
        "user_roles": [role.name for role in user.roles]
    }

@router.put("/change-user-password")
async def change_user_password(
    password_change: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user_data: dict = Depends(require_admin())
):
    user = get_user_by_email(db, password_change.user_email)
    if not user:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "User not found"
        )

    hashed_password = get_password_hash(password_change.new_password)
    user.hashed_password = hashed_password
    db.commit()

    return {
        "message": f"Password changed successfully for {password_change.user_email}"
    }

@router.put("/change-user-company")
async def change_user_company(
    request: ChangeCompanyNameRequest,
    db: Session = Depends(get_db),
    current_user_data: dict = Depends(require_admin())
):
    user = get_user_by_email(db, request.user_email)
    if not user:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "User not found"
        )

    user.company_name = request.new_company_name
    db.commit()

    return {
        "message": f"Company name changed successfully for {request.user_email}"
    }

@router.put("/change-user-email")
async def change_user_email(
    request: ChangeUserEmailRequest,
    db: Session = Depends(get_db),
    current_user_data: dict = Depends(require_admin())
):
    user = get_user_by_email(db, request.old_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    existing_user = get_user_by_email(db, request.new_email)
    if existing_user and existing_user.id != user.id:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail = "Email address is already in use"
        )

    user.email = request.new_email
    db.commit()

    return {
        "message": f"Email changed from {request.old_email} to {request.new_email}"
    }