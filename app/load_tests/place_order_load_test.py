import asyncio
import aiohttp
import json
import time
import statistics
from dataclasses import dataclass
from typing import List, Dict, Any
import random
from datetime import datetime
from dotenv import load_dotenv
import os
from pydantic import BaseModel, EmailStr, Field

load_dotenv()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

@dataclass
class LoadTestConfig:
    base_url: str = "http://localhost:8000"
    endpoint: str = "/orders/place-order"
    concurrent_requests: int = 10
    total_requests: int = 100
    timeout: int = 10

    auth_method: str = "cookie"

    login_endpoint: str = "/auth/login"
    login_email: str = ""
    login_password: str = ""
    cookie_name: str = os.getenv('COOKIE_NAME')

@dataclass
class TestResult:
    status_code: int
    response_time: float
    success: bool
    error: str = ""
    response_data: Dict = None

class OrderLoadTester:
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None
        self.session_cookies = None
    
    async def authenticate(self, session: aiohttp.ClientSession) -> bool:
        if self.config.auth_method == "cookie":
            login_url = f"{self.config.base_url}{self.config.login_endpoint}"
            login_data = UserLogin(
                email = self.config.login_email,
                password = self.config.login_password
            )

            try:
                async with session.post(login_url, json=login_data.dict()) as response:
                    if response.status == 200:
                        response_data = await response.json()

                        if "error" not in response_data:
                            self.session_cookies = session.cookie_jar
                            print(f"Auth. successful for user: {self.config.login_email}")
                            return True
                        else:
                            print(f"Login failed: {response_data.get('error', 'Unknown error')}")
                            return False
                    else:
                        print(f"Login request failed with status: {response.status}")
                        return False
            
            except Exception as e:
                print(f"Auth. error: {str(e)}")
                return False
        return True

    def generate_test_order_data(self) -> Dict[str, Any]:
        sample_products = list(range(1,20))

        order_items = []
        num_items = random.randint(1,5)

        for _ in range(num_items):
            order_items.append({
                "product_id": random.choice(sample_products),
                "quantity": random.randint(1,10)
            })
        return {
            "order_items": order_items
        }

    async def make_request(self, session: aiohttp.ClientSession, request_id: int) -> TestResult:
        url = f"{self.config.base_url}{self.config.endpoint}"
        headers = {
            "Content-Type": "application/json"
        }

        order_data = self.generate_test_order_data()
        start_time = time.time()

        try:
            async with session.post(
                url,
                json=order_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as response:
                response_time = time.time() - start_time

                try:
                    response_data = await response.json()
                except:
                    response_data = {"text": await response.text()}
            
                return TestResult(
                    status_code=response.status,
                    response_time=response_time,
                    success=response.status==200,
                    response_data=response_data
                )
        except asyncio.TimeoutError:
            return TestResult(
                status_code=0,
                response_time=time.time()-start_time,
                success=False,
                error="Request timeout"
            )
        except Exception as e:
            return TestResult(
                status_code=0,
                response_time=time.time() - start_time,
                success=False,
                error=str(e)
            )

    async def run_batch(self, session: aiohttp.ClientSession, batch_size: int) -> List[TestResult]:
        tasks = []
        for i in range(batch_size):
            task = asyncio.create_task(self.make_request(session,i))
            tasks.append(task)
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def run_load_test(self):

        print(f"🚀 Starting load test...")
        print(f"📊 Configuration:")
        print(f"   - Target: {self.config.base_url}{self.config.endpoint}")
        print(f"   - Total requests: {self.config.total_requests}")
        print(f"   - Concurrent requests: {self.config.concurrent_requests}")
        print(f"   - Timeout: {self.config.timeout}s")
        print(f"   - Auth method: {self.config.auth_method}")
        if self.config.auth_method == "cookie":
            print(f"   - Login user: {self.config.login_email}")
        print()

        connector = aiohttp.TCPConnector(
            limit=self.config.concurrent_requests*2,
            limit_per_host=self.config.concurrent_requests,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            if self.config.auth_method == "cookie":
                print("Authenticating...")
                auth_success = await self.authenticate(session)
                if not auth_success:
                    print("Authentication failed. Stopping test.")
                    return
                print()
            self.start_time = time.time()

            remaining_requests=self.config.total_requests
            batch_count = 0

            while remaining_requests > 0:
                batch_size = min(self.config.concurrent_requests, remaining_requests)
                batch_count += 1

                print(f"Running batch: {batch_count} ({batch_size} requests)...")

                batch_results = await self.run_batch(session, batch_size)

                for result in batch_results:
                    if isinstance(result, Exception):
                        self.results.append(TestResult(
                            status_code=0,
                            response_time=0,
                            success=False,
                            error=str(result)
                        ))
                    else:
                        self.results.append(result)
                
                remaining_requests -= batch_size
                
                if remaining_requests > 0:
                    await asyncio.sleep(0.1)

        self.end_time = time.time()
        self.print_results()

    def print_results(self):
        """Print comprehensive test results"""
        total_time = self.end_time - self.start_time
        successful_requests = [r for r in self.results if r.success]
        failed_requests = [r for r in self.results if not r.success]
        
        response_times = [r.response_time for r in successful_requests]
        
        print("="*60)
        print("📊 LOAD TEST RESULTS")
        print("="*60)
        
        # Basic metrics
        print(f"🕐 Total test duration: {total_time:.2f} seconds")
        print(f"📈 Requests per second: {len(self.results)/total_time:.2f}")
        print(f"✅ Successful requests: {len(successful_requests)}")
        print(f"❌ Failed requests: {len(failed_requests)}")
        print(f"📊 Success rate: {(len(successful_requests)/len(self.results)*100):.1f}%")
        print()
        
        # Response time statistics
        if response_times:
            print("⏱️  RESPONSE TIME STATISTICS:")
            print(f"   - Average: {statistics.mean(response_times):.3f}s")
            print(f"   - Median: {statistics.median(response_times):.3f}s")
            print(f"   - Min: {min(response_times):.3f}s")
            print(f"   - Max: {max(response_times):.3f}s")
            if len(response_times) > 1:
                print(f"   - Std Dev: {statistics.stdev(response_times):.3f}s")
            
            # Percentiles
            sorted_times = sorted(response_times)
            p95_idx = int(0.95 * len(sorted_times))
            p99_idx = int(0.99 * len(sorted_times))
            print(f"   - 95th percentile: {sorted_times[p95_idx]:.3f}s")
            if p99_idx < len(sorted_times):
                print(f"   - 99th percentile: {sorted_times[p99_idx]:.3f}s")
        print()
        
        # Status code breakdown
        status_codes = {}
        for result in self.results:
            status_codes[result.status_code] = status_codes.get(result.status_code, 0) + 1
            
        print("📋 STATUS CODE BREAKDOWN:")
        for status_code, count in sorted(status_codes.items()):
            print(f"   - {status_code}: {count} requests")
        print()
        
        # Error analysis
        if failed_requests:
            print("🚨 ERROR ANALYSIS:")
            error_types = {}
            for result in failed_requests:
                error_types[result.error] = error_types.get(result.error, 0) + 1
            
            for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   - {error}: {count} occurrences")
            print()
        
        # Performance classification
        if response_times:
            avg_response_time = statistics.mean(response_times)
            print("🎯 PERFORMANCE ASSESSMENT:")
            if avg_response_time < 0.5:
                print("   - 🟢 Excellent performance (< 0.5s average)")
            elif avg_response_time < 1.0:
                print("   - 🟡 Good performance (< 1.0s average)")
            elif avg_response_time < 2.0:
                print("   - 🟠 Acceptable performance (< 2.0s average)")
            else:
                print("   - 🔴 Poor performance (> 2.0s average)")
            print()

        # Sample successful responses
        if successful_requests:
            print("✅ SAMPLE SUCCESSFUL RESPONSE:")
            sample = successful_requests[0]
            if sample.response_data:
                print(json.dumps(sample.response_data, indent=2)[:500] + "...")
            print()

async def main():

    load_dotenv()
    root_email = os.getenv('ROOT_ADMIN_EMAIL')
    root_password = os.getenv('ROOT_ADMIN_PASSWORD')

    config = LoadTestConfig(
        base_url="http://localhost:8000",         
        endpoint="/orders/place-order",                   
        concurrent_requests=20,                    
        total_requests=200,                        
        timeout=30,                                
        
        auth_method="cookie",
        login_endpoint="/auth/login",                   
        login_email=root_email,            
        login_password=root_password,          
        cookie_name=os.getenv('COOKIE_NAME')         
    )

    if config.auth_method == "cookie" and (not config.login_email or not config.login_password):
        print("⚠️  Warning: Cookie authentication selected but no login credentials provided!")
        print("   Update login_email and login_password in LoadTestConfig.")
        print("   Make sure you have a test user account created for load testing.")
        return

    tester = OrderLoadTester(config)
    await tester.run_load_test()

if __name__ == "__main__":
    asyncio.run(main())