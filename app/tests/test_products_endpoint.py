import requests
import time
from enum import Enum


class ProductCategory(str, Enum):
    CHICKEN = "Hähnchen"
    VEAL = "Kalb"
    LAMB = "Lamm"
    BEEF = "Rind"
    OTHER = "Sonstiges"


BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/products/"


def test_get_all_products():
    print(f"Testing: GET /products/ (all)")
    try:
        response = requests.get(ENDPOINT, timeout=10)
        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            products = response.json()
            print(f"Success! Retrieved {len(products)} products")

            if products:
                print(f"Sample product:")
                print(f" - {products[0]}")
            else:
                print(f"No products found in db!")
        else:
            print(f"Error: {response.text}")

    except requests.exception.RequestException as e:
        print(f"Request failed: {e}")


def test_get_products_by_category():
    print("Testing: GET /products/ (category)")

    for category in ProductCategory:
        print(f"\nTesting category: {category.value}")

        try:
            params = {"category": category.value}
            response = requests.get(ENDPOINT, params=params, timeout=10)
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                products = response.json()
                print(f"Found {len(products)} products in category '{category.value}'")

                if products:
                    sample_product = products[0]
                    print(f"Sample product: {sample_product.get('name', 'N/A')}")
            else:
                print(f"Error: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")

        time.sleep(0.5)


def test_invalid_category():
    print("Testing: Invalid category")

    try:
        params = {"category": "InvalidCategory"}
        response = requests.get(ENDPOINT, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")


def main():
    print("=" * 50)
    print("PRODUCT ENDPOINT LOAD TEST")
    print("=" * 50)

    test_get_all_products()
    test_get_products_by_category()
    test_invalid_category()

    print("\n" + "=" * 50)
    print("Test completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
