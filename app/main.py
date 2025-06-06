from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.config.database import engine, Base
from app.models import user 
from app.routers import user as user_router
from app.routers import auth as auth_router

from fastapi.middleware.cors import CORSMiddleware

from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.middleware.rate_limiter import InMemoryRateLimiter

user.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Grunland API")

@app.get("/")
def read_root():
    return {"message": "Hello"}

@app.get("/health", tags=["Health"])
async def health_check():
    return JSONResponse(content={"status":"ok"})

app.include_router(user_router.router)
app.include_router(auth_router.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#app.add_middleware(InMemoryRateLimiter, login_limit=(5,60), general_limit=(20,60))

#Prod code

"""

#app.add_middleware(GzipMiddleware, minimum_size=1000)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts = []
)
"""
