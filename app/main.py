from fastapi import FastAPI
from app.routers import auth, patients

app = FastAPI(title="Authentication API")

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])

@app.get("/")
def read_root():
    return {"message": "Auth Backend is running"}