import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# NOTE: the above code seems to be necessary to ensure that this test_file can find
# the app.middleware folder, else there is some import issue => Is there another way?

import time

import pytest
import redis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.middleware.rate_limiter import RateLimitConfig, RedisRateLimiter

"""
    Test strategy:

    /products/ is a default route: -> 200 requests per minute
        - send 199 expect 200 OK
        - send 201 -> expect 429 too many requests

    /auth/login -> 10 per 5 min.
        -> send 10 expect 200 OK
        -> send 11 expect 429
"""

redis_conn = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


@pytest.fixture(autouse=True)
def clear_redis():
    redis_conn.flushdb()
    yield
    redis_conn.flushdb()


# Testing the endpoints
def create_test_app():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, redis_connection=redis_conn)

    @app.get("/products/")
    def products():
        return {"message": "ok"}

    @app.post("/auth/login")
    def login():
        return {"message": "logged in"}

    return app


client = TestClient(create_test_app())


def test_products_rate_limit():
    for i in range(200):
        res = client.get("/products/")
        assert res.status_code == 200, f"Failed at request {i+1}"

    res = client.get("/products/")
    assert res.status_code == 429


def test_auth_login_rate_limit():
    for i in range(10):
        res = client.post("/auth/login")
        assert res.status_code == 200, f"Failed at login request {i+1}"

    res = client.post("/auth/login")
    assert res.status_code == 429


def test_default_rate_limit_resets_after_ttl():
    for i in range(200):
        res = client.get("/products/")
        assert res.status_code == 200, f"Failed at request: {i+1}"

    res = client.get("/products/")
    assert res.status_code == 429

    time.sleep(61)

    res = client.get("/products/")
    assert res.status_code == 200


def test_auth_login_rate_limit_resets_after_ttl():
    for i in range(10):
        res = client.post("/auth/login")
        assert res.status_code == 200, f"Failed at login request {i+1}"

    res = client.post("/auth/login")
    assert res.status_code == 429

    time.sleep(360)

    res = client.post("/auth/login")
    assert res.status_code == 200
