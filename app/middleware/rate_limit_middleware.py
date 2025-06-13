from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.rate_limiter import RedisRateLimiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_connection):
        super().__init__(app)
        self.rate_limiter = RedisRateLimiter(redis_connection)

    async def dispatch(self, request: Request, call_next):
        rate_limit_response = self.rate_limiter.check_rate_limit(request)
        if rate_limit_response:
            return rate_limit_response

        response = await call_next(request)

        if hasattr(request.state, "rate_limit_headers"):
            for key, value in request.state.rate_limit_headers.items():
                response.headers.update(request.state.rate_limit_headers)

        return response
