import requests
import time
import threading
import random
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import statistics


class ProductCategory(str, Enum):
    CHICKEN = "Hähnchen"
    VEAL = "Kalb"
    LAMB = "Lamm"
    BEEF = "Rind"
    OTHER = "Sonstiges"


BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/products/"
REQUESTS_PER_SECOND = 10
DURATION_SECONDS = 30
TOTAL_REQUESTS = REQUESTS_PER_SECOND * DURATION_SECONDS

results = []
lock = threading.Lock()
stop_stats = threading.Event()


def make_request(request_id):
    start_time = time.time()

    if random.choice([True, False]):
        url = ENDPOINT
        params = None
        request_type = "all_products"
    else:
        category = random.choice(list(ProductCategory))
        url = ENDPOINT
        params = {"category": category.value}
        request_type = f"category_{category.name.lower()}"

    try:
        response = requests.get(url, params=params, timeout=10)
        end_time = time.time()
        response_time = end_time - start_time

        result = {
            "request_id": request_id,
            "request_type": request_type,
            "status_code": response.status_code,
            "response_time": response_time,
            "success": response.status_code == 200,
            "error": None,
            "timestamp": start_time,
        }

        try:
            if response.status_code == 200:
                data = response.json()
                result["products_count"] = len(data) if isinstance(data, list) else 1
            else:
                result["products_count"] = 0
        except:
            result["products_count"] = 0

    except requests.exceptions.Timeout:
        end_time = time.time()
        result = {
            "request_id": request_id,
            "request_type": request_type,
            "status_code": 0,
            "response_time": end_time - start_time,
            "success": False,
            "error": "Timeout",
            "products_count": 0,
            "timestamp": start_time,
        }
    except Exception as e:
        end_time = time.time()
        result = {
            "request_id": request_id,
            "request_type": request_type,
            "status_code": 0,
            "response_time": end_time - start_time,
            "success": False,
            "error": str(e),
            "products_count": 0,
            "timestamp": start_time,
        }

    with lock:
        results.append(result)

    return result


def print_live_stats():
    while not stop_stats.is_set():
        time.sleep(5)

        with lock:
            if not results:
                continue

            total_requests = len(results)
            successful_requests = sum(1 for r in results if r["success"])
            failed_requests = total_requests - successful_requests

            if total_requests > 0:
                success_rate = (successful_requests / total_requests) * 100
                avg_response_time = statistics.mean(r["response_time"] for r in results)

                print(
                    f"\n[LIVE] Requests: {total_requests}/{TOTAL_REQUESTS} | "
                    f"Success: {success_rate:.1f}% | "
                    f"Avg Response: {avg_response_time:.3f}s"
                )


def run_load_test():
    """Run the load test"""
    print("=" * 60)
    print(f"LOAD TESTING: {REQUESTS_PER_SECOND} req/sec for {DURATION_SECONDS} seconds")
    print(f"Total requests: {TOTAL_REQUESTS}")
    print("=" * 60)

    stats_thread = threading.Thread(target=print_live_stats, daemon=True)
    stats_thread.start()

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []

        for i in range(TOTAL_REQUESTS):
            future = executor.submit(make_request, i + 1)
            futures.append(future)

            if (i + 1) % REQUESTS_PER_SECOND == 0:
                elapsed = time.time() - start_time
                expected_time = (i + 1) / REQUESTS_PER_SECOND
                if elapsed < expected_time:
                    time.sleep(expected_time - elapsed)

        print("\nWaiting for all requests to complete...")
        for future in as_completed(futures):
            pass

    stop_stats.set()

    end_time = time.time()
    total_duration = end_time - start_time

    print(f"\nLoad test completed in {total_duration:.2f} seconds")
    return total_duration


def analyze_results():

    if not results:
        print("No results to analyze!")
        return

    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)

    total_requests = len(results)
    successful_requests = sum(1 for r in results if r["success"])
    failed_requests = total_requests - successful_requests
    success_rate = (successful_requests / total_requests) * 100

    print(f"Total Requests: {total_requests}")
    print(f"Successful: {successful_requests}")
    print(f"Failed: {failed_requests}")
    print(f"Success Rate: {success_rate:.2f}%")

    response_times = [r["response_time"] for r in results]
    if response_times:
        print(f"\nResponse Time Statistics:")
        print(f"  Average: {statistics.mean(response_times):.3f}s")
        print(f"  Median: {statistics.median(response_times):.3f}s")
        print(f"  Min: {min(response_times):.3f}s")
        print(f"  Max: {max(response_times):.3f}s")

        sorted_times = sorted(response_times)
        p95 = sorted_times[int(0.95 * len(sorted_times))]
        p99 = sorted_times[int(0.99 * len(sorted_times))]
        print(f"  95th percentile: {p95:.3f}s")
        print(f"  99th percentile: {p99:.3f}s")

    status_codes = defaultdict(int)
    for r in results:
        status_codes[r["status_code"]] += 1

    print(f"\nStatus Code Breakdown:")
    for status, count in sorted(status_codes.items()):
        percentage = (count / total_requests) * 100
        status_text = (
            "OK" if status == 200 else "ERROR" if status == 0 else "HTTP_ERROR"
        )
        print(f"  {status} ({status_text}): {count} ({percentage:.1f}%)")

    request_types = defaultdict(int)
    for r in results:
        request_types[r["request_type"]] += 1

    print(f"\nRequest Type Breakdown:")
    for req_type, count in sorted(request_types.items()):
        percentage = (count / total_requests) * 100
        print(f"  {req_type}: {count} ({percentage:.1f}%)")

    errors = [r for r in results if not r["success"]]
    if errors:
        print(f"\nError Analysis:")
        error_types = defaultdict(int)
        for error in errors:
            error_type = error["error"] or f"HTTP_{error['status_code']}"
            error_types[error_type] += 1

        for error_type, count in sorted(error_types.items()):
            print(f"  {error_type}: {count}")

    if results:
        first_request = min(r["timestamp"] for r in results)
        last_request = max(r["timestamp"] + r["response_time"] for r in results)
        actual_duration = last_request - first_request
        actual_throughput = successful_requests / actual_duration
        print(f"\nThroughput: {actual_throughput:.2f} successful requests/second")


def main():
    print("Starting load test...")
    print(f"Target: {BASE_URL}/products/")
    print(f"Press Ctrl+C to stop early if needed\n")

    try:
        duration = run_load_test()

        analyze_results()

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user!")
        if results:
            analyze_results()
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        if results:
            analyze_results()


if __name__ == "__main__":
    main()
