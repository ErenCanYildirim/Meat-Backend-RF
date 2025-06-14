import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               generate_latest)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

REQUEST_COUNTS = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

ACTIVE_REQUESTS = Gauge("http_requests_active", "Number of active HTTP requests")

REQUEST_SIZE = Histogram(
    "http_request_size_bytes", "HTTP request size in bytes", ["method", "endpoint"]
)

RESPONSE_SIZE = Histogram(
    "http_response_size_bytes", "HTTP response size in bytes", ["method", "endpoint"]
)

# Custom business metrics

ORDER_COUNT = Counter(
    "business_orders_total", "Total number of orders created", ["status"]
)

USER_REGISTRATIONS = Counter(
    "business_user_registrations_total", "Total number of user registrations"
)

PDF_PROCESSING_TIME = Histogram(
    "business_pdf_processing_duration_seconds", "Time spent processing PDFs"
)

EMAIL_SENT = Counter(
    "business_emails_sent_total", "Total number of emails sent", ["type", "status"]
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path

        ACTIVE_REQUESTS.inc()
        start_time = time.time()
        request_size = int(request.headers.get("content-length", 0))

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            response_size = int(response.headers.get("content-length", 0))

            REQUEST_COUNTS.labels(
                method=method, endpoint=path, status_code=response.status_code
            ).inc()

            REQUEST_DURATION.labels(method=method, endpoint=path).observe(duration)

            REQUEST_SIZE.labels(method=method, endpoint=path).observe(request_size)

            RESPONSE_SIZE.labels(method=method, endpoint=path).observe(response_size)

            return response

        except Exception as e:
            REQUEST_COUNTS.labels(method=method, endpoint=path, status_code=500).inc()

            duration = time.time() - start_time
            REQUEST_DURATION.labels(method=method, endpoint=path).observe(duration)

            raise

        finally:
            ACTIVE_REQUESTS.dec()


def record_order_created(status: str = "success"):
    ORDER_COUNT.labels(status=status).inc()


def record_user_registration():
    USER_REGISTRATIONS.inc()


def record_pdf_processing_time(duration: float):
    PDF_PROCESSING_TIME.observe(duration)


def record_email_sent(email_type: str, status: str = "success"):
    EMAIL_SENT.labels(type=email_type, status=status).inc()
