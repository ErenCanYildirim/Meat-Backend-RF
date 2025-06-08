from fastapi import HTTPException, Depends, Response, Request, status 
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt 
from typing import List, Optional
from app.config.database import get_db

from sqlalchemy.orm import Session
from app.models import User
from pydantic import EmailStr

from app.crud.user import get_user_by_company_name
from app.schemas.user import TokenData

from dotenv import load_dotenv
import os
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", 1))
COOKIE_NAME = os.getenv("COOKIE_NAME", "auth_token")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "login")

def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db:Session, email: EmailStr, password:str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False 
    if not verify_password(password, user.hashed_password):
        return False 
    return user   

#Note: Change to utcnow later
def create_access_token(data:dict, expires_delta:Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms = [ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

async def get_current_user(request:Request, db:Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Could not validate credentials!",
        headers = {"WWW-Authenticate":"Bearer"}, 
    )

    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        company_name: Optional[str] = payload.get("sub")
        if company_name is None:
            raise credentials_exception
        token_data = TokenData(company_name=company_name)
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = get_user_by_company_name(db, token_data.company_name)
    print(f"{user}")
    if user is None:
        raise credentials_exception
    return user 

#Debug
async def get_current_user_debug(request:Request, db:Session = Depends(get_db)):
    print(f"===GET_CURRENT_USER DEBUG===")
    print(f"Request cookies: {dict(request.cookies)}")
    print(f"Looking for cookie: {COOKIE_NAME}")
    
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Could not validate credentials!",
        headers = {"WWW-Authenticate":"Bearer"}, 
    )

    #print(f"All cookies: {request.cookies}")
    token = request.cookies.get(COOKIE_NAME)#
    print(f"Token found: {token is not None}")
    #print(f"Token from cookie: {token}")

    if not token:
        print("No -token - returning 401")
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        #print(f"Decoded payload: {payload}")
        company_name: Optional[str] = payload.get("sub")
        if company_name is None:
            #print("No company name in payload.")
            raise credentials_exception
        token_data = TokenData(company_name=company_name)
    except jwt.PyJWTError:
        #print(f"JWT error: {e}")
        raise credentials_exception
    
    #user = get_user(db, username=token_data.company_name)
    user = get_user_by_company_name(db, token_data.company_name)
    print(f"{user}")
    if user is None:
        #print("User not found")
        raise credentials_exception
    return user 

