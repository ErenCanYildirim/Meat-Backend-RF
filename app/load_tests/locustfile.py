from locust import HttpUser, task, between
import random
import string
import json
from datetime import datetime


class AuthUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.user_id = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        self.email = f"test_{self.user_id}@example.com"
        self.company_name = f"TestCompany_{self.user_id}"
        self.password = "TestPassword123!"
        self.is_registered = False
        self.is_logged_in = False

    def generate_unique_user_data(self):
        user_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return {
            "email": f"loadtest_{user_id}@example.com",
            "company_name": f"LoadTestCompany_{user_id}",
            "password": "LoadTest123!",
        }

    @task(3)
    def register_user(self):
        user_data = self.generate_unique_user_data()

        with self.client.post(
            "/auth/register", json=user_data, catch_response=True
        ) as response:
            if response.status_code == 200:
                response_data = response.json()
                if "error" in response_data:
                    response.failure(f"Registration failed: {response_data['error']}")
                else:
                    response.success()
                    if "Set-Cookie" in response.headers:
                        self.client.cookies.update(response.cookies)
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(5)
    def login_existing_user(self):
        test_users = [
            {"email": "admin@test.com", "password": "admin123"},
            {"email": "user1@test.com", "password": "user123"},
            {"email": "user2@test.com", "password": "user123"},
            {"email": "manager@test.com", "password": "manager123"},
        ]

        user_data = random.choice(test_users)

        with self.client.post(
            "/auth/login", json=user_data, catch_response=True
        ) as response:
            if response.status_code == 200:
                response_data = response.json()
                if "error" in response_data:
                    response.success()
                else:
                    response.success()
                    if "Set-Cookie" in response.headers:
                        self.client.cookies.update(response.cookies)
                        self.is_logged_in = True
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(2)
    def register_and_login_flow(self):
        user_data = self.generate_unique_user_data()

        # Step 1: Register
        with self.client.post(
            "/auth/register", json=user_data, catch_response=True
        ) as reg_response:
            if reg_response.status_code == 200:
                reg_data = reg_response.json()
                if "error" not in reg_data:
                    if "Set-Cookie" in reg_response.headers:
                        self.client.cookies.update(reg_response.cookies)

                    with self.client.get(
                        "/auth/me", catch_response=True
                    ) as me_response:
                        if me_response.status_code == 200:
                            me_response.success()
                        else:
                            me_response.failure(
                                f"Failed to access /me: {me_response.status_code}"
                            )

                    with self.client.get(
                        "/auth/logout", catch_response=True
                    ) as logout_response:
                        if logout_response.status_code == 200:
                            logout_response.success()
                            self.client.cookies.clear()
                        else:
                            logout_response.failure(
                                f"Logout failed: {logout_response.status_code}"
                            )

                    reg_response.success()
                else:
                    reg_response.failure(f"Registration failed: {reg_data['error']}")
            else:
                reg_response.failure(
                    f"Registration request failed: {reg_response.status_code}"
                )

    @task(1)
    def test_me_endpoint_unauthorized(self):
        temp_cookies = self.client.cookies.copy()
        self.client.cookies.clear()

        with self.client.get("/auth/me", catch_response=True) as response:
            if response.status_code == 401:
                response.success()
            else:
                response.failure(f"Expected 401, got {response.status_code}")

        self.client.cookies.update(temp_cookies)

    @task(1)
    def test_logout(self):
        with self.client.get("/auth/logout", catch_response=True) as response:
            if response.status_code == 200:
                response_data = response.json()
                if "message" in response_data:
                    response.success()
                else:
                    response.failure("Logout response missing message")
            else:
                response.failure(f"Logout failed: {response.status_code}")

    @task(1)
    def test_invalid_login(self):
        invalid_data = {"email": "nonexistent@example.com", "password": "wrongpassword"}

        with self.client.post(
            "/auth/login", json=invalid_data, catch_response=True
        ) as response:
            if response.status_code == 200:
                response_data = response.json()
                if "error" in response_data:
                    response.success()
                else:
                    response.failure("Expected error for invalid login")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")


class HighLoadAuthUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.user_id = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=12)
        )

    @task
    def rapid_register_attempts(self):
        """Rapid registration attempts to test rate limiting and performance"""
        user_data = {
            "email": f"rapid_{self.user_id}_{random.randint(1000, 9999)}@example.com",
            "company_name": f"RapidTest_{self.user_id}_{random.randint(1000, 9999)}",
            "password": "RapidTest123!",
        }

        self.client.post("/auth/register", json=user_data)


class StressTestUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self):
        self.session_id = "".join(
            random.choices(string.ascii_letters + string.digits, k=16)
        )

    @task(10)
    def stress_register(self):
        user_data = {
            "email": f"stress_{self.session_id}_{random.randint(10000, 99999)}@test.com",
            "company_name": f"StressCompany_{self.session_id}_{random.randint(10000, 99999)}",
            "password": "StressTest123!",
        }
        self.client.post("/auth/register", json=user_data)

    @task(5)
    def stress_login(self):
        login_data = {
            "email": f"testuser{random.randint(1, 100)}@test.com",
            "password": "testpass123",
        }
        self.client.post("/auth/login", json=login_data)
