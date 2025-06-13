import json
import os

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr, Field


class UserLogin(BaseModel):
    email: EmailStr
    password: str


load_dotenv()

root_email = os.getenv("ROOT_ADMIN_EMAIL")
root_password = os.getenv("ROOT_ADMIN_PASSWORD")

if not root_email or not root_password:
    print(f"No root email/password")


BASE_URL = "http://localhost:8000"
PLACE_ORDER_ENDPOINT = f"{BASE_URL}/orders/place-order"


def test_place_order_with_auth():

    login_data = UserLogin(email=root_email, password=root_password)

    session = requests.Session()
    try:
        print(f"Loggin in with email: {root_email}")
        login_response = session.post(
            f"{BASE_URL}/auth/login", json=login_data.model_dump()
        )
        login_response.raise_for_status()
        login_result = login_response.json()

        if "error" in login_result:
            print(f"Login failed: {login_result['error']}")

        print(f"Auth. successful!")
        print(f"User: {login_result.get('user', {}).get('username')}")
        print(f"Roles: {login_result.get('user', {}).get('roles')}")

    except requests.exceptions.RequestException as e:
        print(f"Login failed: {e}")
        return

    order_data = {
        "order_items": [
            {"product_id": 1, "quantity": 2},
            {"product_id": 5, "quantity": 1},
            {"product_id": 10, "quantity": 3},
        ]
    }

    try:
        print(f"Placing order...")
        print(f"Order data: {json.dumps(order_data, indent=2)}")

        response = session.post(
            PLACE_ORDER_ENDPOINT,
            json=order_data,
            headers={"Content-Type": "application/json"},
        )

        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Order placed successfully!")
            print(f"Order ID: {result.get('id')}")
            print(f"User Email: {result.get('user_email')}")
            print(f"Order State: {result.get('state')}")
            print(f"Order Date: {result.get('order_date')}")
            print(f"PDF Job ID: {result.get('queue_info', {}).get('pdf_job_id')}")
            print(f"Queue Message: {result.get('queue_info', {}).get('message')}")

            print("\nOrder Items:")
            for item in result.get("order_items", []):
                product = item.get("product", {})
                print(
                    f"  - Product ID: {item.get('product_id')}, Quantity: {item.get('quantity')}"
                )
                print(f"    Description: {product.get('description', 'N/A')}")
                print(f"    Category: {product.get('category', 'N/A')}")

            print(f"\nFull Response: {json.dumps(result, indent=2, default=str)}")
        else:
            print(f"❌ Order failed: {response.status_code}")
            print(f"Error: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")


def test_place_order_without_auth():
    order_data = {"order_items": [{"product_id": 1, "quantity": 1}]}

    try:
        print("Testing without auth. (should fail with 401)...")
        response = requests.post(PLACE_ORDER_ENDPOINT, json=order_data)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 401:
            print("Correctly rejected unauth. request")
        else:
            print("⚠️ Expected 401 Status code")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")


def check_products():
    """Helper function to check what products exist (if endpoint exists)"""
    try:
        print("\n📋 Checking available products...")
        response = requests.get(f"{BASE_URL}/products")
        if response.status_code == 200:
            products = response.json()
            print(f"Found {len(products)} products:")
            for i, product in enumerate(products[:5]):  # Show first 5
                print(
                    f"  ID: {product.get('id')}, Description: {product.get('description', 'N/A')}"
                )
            if len(products) > 5:
                print(f"  ... and {len(products) - 5} more")
        else:
            print(f"Products endpoint returned: {response.status_code}")
            print("(This is okay if you don't have a products endpoint)")
    except requests.exceptions.RequestException as e:
        print(f"Could not fetch products: {e}")
        print("(This is okay if you don't have a products endpoint)")


if __name__ == "__main__":
    print("🧪 Testing Place Order Endpoint")
    print("=" * 50)

    # Check environment variables
    root_email = os.getenv("ROOT_ADMIN_EMAIL")
    root_password = os.getenv("ROOT_ADMIN_PASSWORD")

    if not root_email or not root_password:
        print("❌ Please set environment variables first:")
        print("export ROOT_ADMIN_EMAIL=your_admin_email")
        print("export ROOT_ADMIN_PASSWORD=your_admin_password")
        exit(1)

    # Check what products are available (optional)
    check_products()

    # Test without authentication
    test_place_order_without_auth()

    # Test with authentication
    print("\n" + "=" * 50)
    test_place_order_with_auth()
