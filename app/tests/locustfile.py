import random
import string
from locust import HttpUser, task, between
from faker import Faker

fake = Faker()


class AuthUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.user_data = None
        self.is_logged_in = False
        self.cookies = {}

    def generate_unique_user_data(self):
        random_suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        return {
            "email": f"test_{random_suffix}@example.com",
            "password": "TestPassword123!",
            "company_name": f"TestCompany_{random_suffix}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
        }

    @task(2)
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
                    self.user_data = user_data
                    self.is_logged_in = True
                    self.cookies = response.cookies
                    response.success()
            else:
                response.failure(
                    f"Registration failed with status {response.status_code}"
                )

    @task(3)
    def login_user(self):

        if not self.user_data:
            self.user_data = self.generate_unique_user_data()

            self.client.post("/auth/register", json=self.user_data)

        login_data = {
            "email": self.user_data["email"],
            "password": self.user_data["password"],
        }

        with self.client.post(
            "/auth/login", json=login_data, catch_response=True
        ) as response:
            if response.status_code == 200:
                response_data = response.json()
                if "error" in response_data:
                    response.failure(f"Login failed: {response_data['error']}")
                else:
                    self.is_logged_in = True
                    self.cookies = response.cookies
                    response.success()
            else:
                response.failure(f"Login failed with status {response.status_code}")

    @task(4)
    def get_current_user(self):

        if not self.is_logged_in:
            # Login first
            self.login_user()

        with self.client.get(
            "/auth/me", cookies=self.cookies, catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:

                self.is_logged_in = False
                response.failure("Unauthorized - token expired or invalid")
            else:
                response.failure(
                    f"Get current user failed with status {response.status_code}"
                )

    @task(1)
    def logout_user(self):

        if self.is_logged_in:
            with self.client.get(
                "/auth/logout", cookies=self.cookies, catch_response=True
            ) as response:
                if response.status_code == 200:
                    self.is_logged_in = False
                    self.cookies = {}
                    response.success()
                else:
                    response.failure(
                        f"Logout failed with status {response.status_code}"
                    )

    @task(1)
    def test_duplicate_email_registration(self):

        if self.user_data:
            duplicate_data = self.user_data.copy()
            duplicate_data["company_name"] = (
                f"DifferentCompany_{random.randint(1000, 9999)}"
            )

            with self.client.post(
                "/auth/register", json=duplicate_data, catch_response=True
            ) as response:
                if response.status_code == 200:
                    response_data = response.json()
                    if (
                        "error" in response_data
                        and "already registered" in response_data["error"]
                    ):
                        response.success()
                    else:
                        response.failure("Expected duplicate email error not returned")
                else:
                    response.failure(
                        f"Duplicate email test failed with status {response.status_code}"
                    )

    @task(1)
    def test_duplicate_company_registration(self):

        if self.user_data:
            duplicate_data = self.user_data.copy()
            duplicate_data["email"] = (
                f"different_{random.randint(1000, 9999)}@example.com"
            )

            with self.client.post(
                "/auth/register", json=duplicate_data, catch_response=True
            ) as response:
                if response.status_code == 200:
                    response_data = response.json()
                    if (
                        "error" in response_data
                        and "already taken" in response_data["error"]
                    ):
                        response.success()
                    else:
                        response.failure(
                            "Expected duplicate company error not returned"
                        )
                else:
                    response.failure(
                        f"Duplicate company test failed with status {response.status_code}"
                    )

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
                    response.failure("Expected login error not returned")
            else:
                response.failure(
                    f"Invalid login test failed with status {response.status_code}"
                )

    @task(1)
    def test_unauthorized_access(self):

        with self.client.get("/auth/me", catch_response=True) as response:
            if response.status_code == 401:
                response.success()
            else:
                response.failure(
                    f"Expected 401 unauthorized, got {response.status_code}"
                )


class AuthUserScenario(HttpUser):

    wait_time = between(2, 5)

    def on_start(self):
        self.user_data = None
        self.is_logged_in = False
        self.cookies = {}

    def generate_unique_user_data(self):
        random_suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        return {
            "email": f"scenario_{random_suffix}@example.com",
            "password": "TestPassword123!",
            "company_name": f"ScenarioCompany_{random_suffix}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
        }

    @task
    def user_journey(self):

        # Register
        if not self.user_data:
            self.user_data = self.generate_unique_user_data()
            response = self.client.post("/auth/register", json=self.user_data)
            if response.status_code == 200 and "error" not in response.json():
                self.is_logged_in = True
                self.cookies = response.cookies

        # Check profile multiple times
        for _ in range(random.randint(2, 5)):
            if self.is_logged_in:
                self.client.get("/auth/me", cookies=self.cookies)
                self.wait()

        # Logout
        if self.is_logged_in:
            self.client.get("/auth/logout", cookies=self.cookies)
            self.is_logged_in = False
            self.cookies = {}

        # Login again
        if self.user_data:
            login_data = {
                "email": self.user_data["email"],
                "password": self.user_data["password"],
            }
            response = self.client.post("/auth/login", json=login_data)
            if response.status_code == 200 and "error" not in response.json():
                self.is_logged_in = True
                self.cookies = response.cookies

        # check profile again
        if self.is_logged_in:
            for _ in range(random.randint(1, 3)):
                self.client.get("/auth/me", cookies=self.cookies)
                self.wait()
