import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.rate_limiter import InMemoryRateLimiter

# A new test client will be provided, as the ip is shared here


def create_test_client():
    app = FastAPI()

    @app.get("/some-endpoint")
    async def some_endpoint():
        return {"message": "OK"}

    @app.post("/auth/login")
    async def login():
        return {"message": "Logged in"}

    app.add_middleware(InMemoryRateLimiter, login_limit=(5, 60), general_limit=(20, 60))

    return TestClient(app)


def test_login_rate_limit():
    client = create_test_client()

    for i in range(5):
        res = client.post("/auth/login")
        assert res.status_code == 200, f"Failed at request {i+1}"

    res = client.post("/auth/login")
    assert res.status_code == 429
    assert "Too many requests" in res.text


def test_general_rate_limit():
    client = create_test_client()

    for i in range(20):
        res = client.get("/some-endpoint")
        assert res.status_code == 200, f"Failed at request {i+1}"

    res = client.get("/some-endpoint")
    assert res.status_code == 429
    assert "Too many requests" in res.text


def test_rate_limit_reset():
    client = create_test_client()

    for i in range(5):
        client.post("/auth/login")

    assert client.post("/auth/login").status_code == 429

    time.sleep(61)

    res = client.post("/auth/login")
    assert res.status_code == 200
