from fastapi import FastAPI
from app.config.database import engine, Base
from app.models import user 
from app.routers import user as user_router
from app.routers import auth as auth_router

user.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Grunland API")

@app.get("/")
def read_root():
    return {"message": "Hello"}

app.include_router(user_router.router)
app.include_router(auth_router.router)