from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str 
    new_password: str