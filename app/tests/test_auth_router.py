import os
import warnings
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.config.database import get_db
from app.models.base import Base
from app.models.user import User
from app.auth.core import get_password_hash, COOKIE_NAME

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Use real on-disk SQLite file for testing
SQLITE_DATABASE_URL = "sqlite:///./test_grunland.db"
engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency override for get_db
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ----------------------------
# Fixtures
# ----------------------------


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """Setup and teardown the real SQLite DB"""
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_grunland.db"):
        os.remove("test_grunland.db")
    """

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

    engine.dispose()
    Base.metadata.drop_all(bind=engine)

    import time

    time.sleep(0.1)

    try:
        if os.path.exists("test_grunland.db"):
            os.remove("test_grunland.db")
    except PermissionError:
        pass


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def user_data():
    return {
        "email": "test@example.com",
        "password": "testpass123",
        "company_name": "TestCo",
    }


@pytest.fixture
def created_user(db, user_data):
    user = User(
        email=user_data["email"],
        hashed_password=get_password_hash(user_data["password"]),
        company_name=user_data["company_name"],
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(autouse=True)
def clean_users(db):
    db.query(User).delete()
    db.commit()


# ----------------------------
# Test Suites
# ----------------------------


class TestRegistration:
    def test_successful_registration(self, client, user_data):
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == user_data["email"]
        assert data["user"]["username"] == user_data["company_name"]
        assert COOKIE_NAME in response.cookies

    def test_duplicate_email(self, client, created_user, user_data):
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"] == "Email already registered!"

    def test_duplicate_company_name(self, client, created_user):
        new_user_data = {
            "email": "new@example.com",
            "password": "testpass123",
            "company_name": created_user.company_name,
        }
        response = client.post("/auth/register", json=new_user_data)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"] == "Company name already taken!"


class TestLogin:
    def test_successful_login(self, client, created_user, user_data):
        response = client.post(
            "/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == user_data["email"]
        assert COOKIE_NAME in response.cookies

    def test_wrong_password(self, client, created_user, user_data):
        response = client.post(
            "/auth/login",
            json={"email": user_data["email"], "password": "wrongpassword"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"] == "Falscher Nutzername oder Passwort!"

    def test_nonexistent_user(self, client):
        response = client.post(
            "/auth/login", json={"email": "nonexistent@example.com", "password": "pass"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"] == "Falscher Nutzername oder Passwort!"


class TestLogout:
    def test_logout(self, client):
        response = client.get("/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully logged out"


class TestAuthenticatedEndpoints:
    def test_me_endpoint_with_auth(self, client, created_user, user_data):
        print(f"=== TEST DEBUG ===")
        print(
            f"Created user: ID={created_user.id}, Email={created_user.email}, Company={created_user.company_name}"
        )
        print(f"User data: {user_data}")

        login_response = client.post(
            "/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]},
        )
        print(f"Login response status: {login_response.status_code}")
        print(f"Login response body: {login_response.json()}")

        assert login_response.status_code == 200

        cookies = login_response.cookies
        print(f"Cookies from login: {cookies}")

        response = client.get("/auth/me", cookies=cookies)
        print(f"Me response status: {response.status_code}")

        if response.status_code != 200:
            print(f"Me response error: {response.json()}")
        else:
            print(f"Me response success: {response.json()}")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["company_name"] == user_data["company_name"]

    def test_me_endpoint_without_auth(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401


class TestCookies:
    def test_cookie_set_on_registration(self, client, user_data):
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 200
        assert COOKIE_NAME in response.cookies
        cookie_header = response.headers.get("set-cookie", "")
        assert "HttpOnly" in cookie_header
        assert "SameSite=lax" in cookie_header

    def test_cookie_set_on_login(self, client, created_user, user_data):
        response = client.post(
            "/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]},
        )
        assert response.status_code == 200
        assert COOKIE_NAME in response.cookies
        cookie_header = response.headers.get("set-cookie", "")
        assert "HttpOnly" in cookie_header
        assert "SameSite=lax" in cookie_header


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
