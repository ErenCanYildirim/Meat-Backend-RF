from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from starlette.responses import JSONResponse
import time
from typing import Dict, Tuple
from collections import defaultdict


class InMemoryRateLimiter(BaseHTTPMiddleware):
    def __init__(
        self, app, login_limit: Tuple[int, int], general_limit: Tuple[int, int]
    ):
        super().__init__(app)
        self.login_limit = login_limit
        self.general_limit = general_limit
        self.requests: Dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host
        path = request.url.path
        now = time.time()

        if path.startswith("/auth/login"):
            max_req, period = self.login_limit
        else:
            max_req, period = self.general_limit

        window = self.requests[ip]
        self.requests[ip] = [t for t in window if now - t < period]

        if len(self.requests[ip]) >= max_req:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Too many requests from {ip}. Try again later."},
            )

        self.requests[ip].append(now)
        return await call_next(request)
