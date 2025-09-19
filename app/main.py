from fastapi import FastAPI
from app.routers import auth

app = FastAPI(title="Authentication API")

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

@app.get("/")
def read_root():
    return {"message": "Auth Backend is running"}