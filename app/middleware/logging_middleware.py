import json
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config.logging_config import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())

        start_time = time.time()

        method = request.method
        url = str(request.url)
        headers = dict(request.headers)

        logger.info(
            "Request started",
            request_id=request_id,
            method=method,
            url=url,
            client_ip=request.client.host if request.client else None,
            user_agent=headers.get("user-agent"),
        )

        request.state.request_id = request_id

        try:
            response = await call_next(request)

            duration = time.time() - start_time

            logger.info(
                "Request completed",
                request_id=request_id,
                method=method,
                url=url,
                status_code=response.status_code,
                duration=round(duration, 3),
            )

            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration = time.time() - start_time

            logger.error(
                "Request failed",
                request_id=request_id,
                method=method,
                url=url,
                duration=round(duration, 3),
                error=str(e),
                exc_info=True,
            )

            raise
