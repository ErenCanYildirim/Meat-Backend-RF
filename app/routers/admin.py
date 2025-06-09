from fastapi import APIRouter, Depends
from app.auth.dependencies import require_admin, require_manager, require_customer
from app.auth.core import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/admin/dashboard", dependencies=[Depends(require_admin())])
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

