import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch
from app.main import app 
from app.config.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate