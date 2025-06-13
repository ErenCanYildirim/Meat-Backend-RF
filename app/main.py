import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config.database import Base, engine, init_database
from app.config.init_products import initialize_products
from app.config.redis_config import get_redis_connection
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.models.user import Role, User
from app.routers import admin as admin_router
from app.routers import analytics as analytics_router
from app.routers import auth as auth_router
from app.routers import order as order_router
from app.routers import product as product_router
from app.routers import user as user_router


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
    yield
    print("Application shutdown complete!")


app = FastAPI(title="Grunland API", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

redis_conn = get_redis_connection()
app.add_middleware(RateLimitMiddleware, redis_connection=redis_conn)


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


app.include_router(user_router.router)
app.include_router(auth_router.router)
app.include_router(product_router.router)
app.include_router(order_router.router)
app.include_router(admin_router.router)
app.include_router(analytics_router.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
