from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config.database import engine, Base
from app.models.user import Role, User

from app.routers import user as user_router
from app.routers import auth as auth_router
from app.routers import admin as admin_router
from app.routers import product as product_router
from app.routers import order as order_router

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.middleware.rate_limiter import InMemoryRateLimiter
from app.config.database import init_database
from contextlib import asynccontextmanager
import sys
from app.config.init_products import initialize_products

# app.add_middleware(InMemoryRateLimiter, login_limit=(5,60), general_limit=(20,60))


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


app = FastAPI(title="Grundland API", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def read_root():
    return {"message": "Hello"}


@app.get("/health", tags=["Health"])
async def health_check():
    return JSONResponse(content={"status": "ok"})


app.include_router(user_router.router)
app.include_router(auth_router.router)
app.include_router(product_router.router)
app.include_router(order_router.router)
app.include_router(admin_router.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
