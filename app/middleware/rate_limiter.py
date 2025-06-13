import time
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import redis
import json
import hashlib
from datetime import datetime, timedelta


class RateLimitConfig:

    def __init__(
        self, requests: int, window: int, message: Optional[str] = None  # seconds
    ):
        self.requests = requests
        self.window = window
        self.message = (
            message
            or f"Rate limit exceeded. Maximum {requests} requests per {window} seconds."
        )


class RedisRateLimiter:
    """Redis-based rate limiter with sliding window algorithm"""

    def __init__(self, redis_connection: redis.Redis):
        self.redis = redis_connection

        self.default_limits = {
            "/auth/login": RateLimitConfig(10, 300),  # 10 attempts per 6 minutes
            "/auth/register": RateLimitConfig(3, 600),  # 3 attempts per 11 minutes
            "default": RateLimitConfig(200, 60),
        }

        # self.strict_limits = {
        #   "/auth/login": RateLimitConfig(10, 3600),
        #  "/auth/register": RateLimitConfig(5, 3600),
        # }

    def _get_client_ip(self, request: Request) -> str:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _get_rate_limit_key(
        self, ip: str, endpoint: str, window_type: str = "default"
    ) -> str:
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]
        return f"rate_limit:{window_type}:{endpoint}:{ip_hash}"

    def _is_rate_limited(
        self, key: str, config: RateLimitConfig, current_time: float
    ) -> Dict[str, Any]:

        pipeline = self.redis.pipeline()

        pipeline.zremrangebyscore(key, 0, current_time - config.window)

        pipeline.zcard(key)

        pipeline.zadd(key, {str(current_time): current_time})

        pipeline.expire(key, config.window + 60)

        results = pipeline.execute()

        current_count = results[1]

        if current_count >= config.requests:
            oldest_requests = self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_requests:
                oldest_time = oldest_requests[0][1]
                reset_time = oldest_time + config.window
            else:
                reset_time = current_time + config.window

            return {
                "limited": True,
                "current_count": current_count + 1,
                "limit": config.requests,
                "window": config.window,
                "reset_time": reset_time,
                "retry_after": int(reset_time - current_time),
            }

        return {
            "limited": False,
            "current_count": current_count + 1,
            "limit": config.requests,
            "window": config.window,
            "reset_time": current_time + config.window,
            "retry_after": 0,
        }

    def check_rate_limit(self, request: Request) -> Optional[JSONResponse]:

        try:
            ip = self._get_client_ip(request)
            endpoint = request.url.path
            current_time = time.time()

            normalized_endpoint = endpoint.rstrip("/")

            config = self.default_limits.get(
                normalized_endpoint, self.default_limits["default"]
            )

            key = self._get_rate_limit_key(ip, normalized_endpoint)
            result = self._is_rate_limited(key, config, current_time)

            """
            if normalized_endpoint in self.strict_limits:
                strict_config = self.strict_limits[normalized_endpoint]
                strict_key = self._get_rate_limit_key(ip, normalized_endpoint, "strict")
                strict_result = self._is_rate_limited(
                    strict_key, strict_config, current_time
                )

                if strict_result["limited"]:
                    result = strict_result
                    config = strict_config
            """

            headers = {
                "X-RateLimit-Limit": str(config.requests),
                "X-RateLimit-Window": str(config.window),
                "X-RateLimit-Remaining": str(
                    max(0, config.requests - result["current_count"])
                ),
                "X-RateLimit-Reset": str(int(result["reset_time"])),
            }

            if result["limited"]:
                headers["Retry-After"] = str(result["retry_after"])

                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": config.message,
                        "retry_after": result["retry_after"],
                        "limit": config.requests,
                        "window": config.window,
                    },
                    headers=headers,
                )

            request.state.rate_limit_headers = headers

        except Exception as e:
            print(f"Rate limiting error: {e}")

        return None
