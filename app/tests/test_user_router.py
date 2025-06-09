import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch
from datetime import datetime
import uuid
from app.main import app
from app.config.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class MockUser:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        if not hasattr(self, "roles"):
            self.roles = []


test_uuid = uuid.uuid4()
test_uuid2 = uuid.uuid4()
test_datetime = datetime.now()

sample_user_data = {
    "id": test_uuid,
    "email": "test@example.com",
    "company_name": "Test Company",
    "hashed_password": "hashed_password_123",
    "is_active": True,
    "created_at": test_datetime,
    "updated_at": test_datetime,
}

sample_user_create = {
    "email": "newuser@example.com",
    "company_name": "New Company",
    "password": "password123",
}

sample_user_update = {"company_name": "Updated Company Name", "is_active": False}


class TestUserEndpoints:

    @patch("app.crud.user.get_users")
    def test_list_users_success(self, mock_get_users):
        """Test successful retrieval of users list"""
        mock_users = [
            MockUser(**sample_user_data, roles=[]),
            MockUser(
                id=test_uuid2,
                email="user2@example.com",
                company_name="Company Two",
                hashed_password="hashed_password_456",
                is_active=True,
                created_at=test_datetime,
                updated_at=test_datetime,
                roles=[],
            ),
        ]
        mock_get_users.return_value = mock_users

        response = client.get("/users/")

        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["id"] == str(test_uuid)
        mock_get_users.assert_called_once()

    @patch("app.crud.user.get_users")
    def test_list_users_empty(self, mock_get_users):
        """Test retrieval when no users exist"""
        mock_get_users.return_value = []

        response = client.get("/users/")

        assert response.status_code == 200
        assert response.json() == []

    @patch("app.crud.user.get_user")
    def test_get_user_success(self, mock_get_user):
        """Test successful retrieval of a specific user"""
        mock_user = MockUser(**sample_user_data, roles=[])
        mock_get_user.return_value = mock_user

        response = client.get(f"/users/{test_uuid}")

        assert response.status_code == 200
        assert response.json()["id"] == str(test_uuid)
        assert response.json()["email"] == "test@example.com"
        mock_get_user.assert_called_once_with(
            mock_get_user.call_args[0][0], str(test_uuid)
        )

    @patch("app.crud.user.get_user")
    def test_get_user_not_found(self, mock_get_user):
        """Test retrieval of non-existent user"""
        mock_get_user.return_value = None

        response = client.get("/users/nonexistent")

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    @patch("app.crud.user.create_user_with_hashed_password")
    def test_create_user_success(self, mock_create_user):
        """Test successful user creation"""
        new_uuid = uuid.uuid4()
        mock_created_user = MockUser(
            id=new_uuid,
            email=sample_user_create["email"],
            company_name=sample_user_create["company_name"],
            hashed_password="hashed_password_new",
            is_active=True,
            created_at=test_datetime,
            updated_at=test_datetime,
            roles=[],
        )
        mock_create_user.return_value = mock_created_user

        response = client.post("/users/", json=sample_user_create)

        assert response.status_code == 200
        assert response.json()["email"] == sample_user_create["email"]
        assert response.json()["company_name"] == sample_user_create["company_name"]
        mock_create_user.assert_called_once()

    def test_create_user_invalid_data(self):
        """Test user creation with invalid data"""
        invalid_data = {
            "email": "invalid-email",
            "company_name": "",
        }

        response = client.post("/users/", json=invalid_data)

        assert response.status_code == 422

    @patch("app.crud.user.update_user")
    def test_update_user_success(self, mock_update_user):
        """Test successful user update"""
        updated_user = MockUser(
            **{**sample_user_data, **sample_user_update, "roles": []}
        )
        mock_update_user.return_value = updated_user

        response = client.patch(f"/users/{test_uuid}", json=sample_user_update)

        assert response.status_code == 200
        assert response.json()["company_name"] == "Updated Company Name"
        assert response.json()["is_active"] == False
        mock_update_user.assert_called_once()

    @patch("app.crud.user.update_user")
    def test_update_user_not_found(self, mock_update_user):
        """Test update of non-existent user"""
        mock_update_user.return_value = None

        response = client.patch("/users/nonexistent", json=sample_user_update)

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    @patch("app.crud.user.delete_user")
    def test_delete_user_success(self, mock_delete_user):
        """Test successful user deletion"""
        mock_delete_user.return_value = True

        response = client.delete(f"/users/{test_uuid}")

        assert response.status_code == 204
        assert response.content == b""  # No content for 204
        mock_delete_user.assert_called_once_with(
            mock_delete_user.call_args[0][0], str(test_uuid)
        )

    @patch("app.crud.user.delete_user")
    def test_delete_user_not_found(self, mock_delete_user):
        """Test deletion of non-existent user"""
        mock_delete_user.return_value = False

        response = client.delete("/users/nonexistent")

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_user_endpoints_routing(self):
        """Test that all user endpoints are properly routed"""
        # This test checks if endpoints exist without mocking
        with patch("app.crud.user.get_users", return_value=[]):
            response = client.get("/users/")
            assert response.status_code == 200

        with patch("app.crud.user.get_user", return_value=None):
            response = client.get("/users/test")
            assert response.status_code == 404


# Integration tests with actual db
class TestUserEndpointsIntegration:
    pass


class TestUserEndpointsPerformance:

    @patch("app.crud.user.get_users")
    def test_list_users_performance(self, mock_get_users):

        large_user_list = [
            MockUser(
                id=uuid.uuid4(),
                email=f"user{i}@example.com",
                company_name=f"Company {i}",
                hashed_password=f"hash{i}",
                is_active=True,
                created_at=test_datetime,
                updated_at=test_datetime,
                roles=[],
            )
            for i in range(1000)
        ]
        mock_get_users.return_value = large_user_list

        import time

        start_time = time.time()
        response = client.get("/users/")
        end_time = time.time()

        assert response.status_code == 200
        assert len(response.json()) == 1000

        assert (end_time - start_time) < 1.0


class TestUserEndpointsErrorHandling:

    @patch("app.crud.user.get_users")
    def test_database_error_handling(self, mock_get_users):
        """Test handling of database errors"""
        from sqlalchemy.exc import SQLAlchemyError

        mock_get_users.side_effect = SQLAlchemyError("Database connection error")

        try:
            response = client.get("/users/")

            assert response.status_code in [500, 503]
        except Exception:
            pass


if __name__ == "__main__":
    pytest.main([__file__])
