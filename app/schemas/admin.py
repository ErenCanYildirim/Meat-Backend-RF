from pydantic import BaseModel, EmailStr, Field

class ChangeUserRoleRequest(BaseModel):
    user_email: EmailStr
    new_role: str
    remove_existing_roles: bool = False

class ChangePasswordRequest(BaseModel):
    user_email: EmailStr
    new_password: str

class ChangeCompanyNameRequest(BaseModel):
    user_email: EmailStr
    new_company_name: str 

class ChangeUserEmailRequest(BaseModel):
    old_email: EmailStr
    new_email: EmailStr