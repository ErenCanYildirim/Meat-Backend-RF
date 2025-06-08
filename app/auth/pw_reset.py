from app.models.password_reset import PasswordResetToken
from app.schemas.password import ForgotPasswordRequest, ResetPasswordRequest
from .core import pwd_context

from datetime import datetime, timedelta
import secrets

def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)