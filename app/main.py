import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config.database import Base, engine, init_database
from app.config.init_products import initialize_products
from app.config.logging_config import get_logger, setup_logging
from app.config.redis_config import get_redis_connection
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.prometheus_middleware import PrometheusMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.models.user import Role, User
from app.routers import admin as admin_router
from app.routers import analytics as analytics_router
from app.routers import auth as auth_router
from app.routers import ml_router as ml_router
from app.routers import order as order_router
from app.routers import product as product_router
from app.routers import user as user_router

from app.config.db_faker import populate_dummy_data


environment = os.getenv("ENVIRONMENT", "development")
setup_logging(environment)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("Starting application...")
        init_database()
        print("Database initialized succesfully")
    except Exception as e:
        print(f"Failed to init. db: {e}")
        print("Application startup failed. Exiting...")
        sys.exit(1)
    try:
        # print("Adding products")
        initialize_products()
        # print("Products initialized")
    except Exception as e:
        print(f"Failed to initialize products!")
    #populate_dummy_data() #for testing purposes
    yield
    print("Application shutdown complete!")


app = FastAPI(title="Grunland API", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

redis_conn = get_redis_connection()
app.add_middleware(RateLimitMiddleware, redis_connection=redis_conn)
app.add_middleware(LoggingMiddleware)
app.add_middleware(PrometheusMiddleware)


@app.get("/")
def read_root():
    return {"message": "Hello"}


@app.get("/health", tags=["Health"])
async def health_check():
    # return JSONResponse(content={"status": "ok"})
    try:
        redis_conn = get_redis_connection()
        redis_conn.ping()
        return {"status": "healthy", "database": "connected", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/endpoints", tags=["Debug"])
async def list_all_endpoints():
    openapi = app.openapi()
    endpoints = []
    for path, methods in openapi["paths"].items():
        for method, details in methods.items():
            endpoints.append({
                "path": path,
                "method": method.upper(),
                "operationId": details.get("operationId", ""),
                "summary": details.get("summary", ""),
            })
    return JSONResponse(content=endpoints)

app.include_router(user_router.router)
app.include_router(auth_router.router)
app.include_router(product_router.router)
app.include_router(order_router.router)
app.include_router(admin_router.router)
app.include_router(analytics_router.router)
app.include_router(ml_router.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
