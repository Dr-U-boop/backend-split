from fastapi import FastAPI
from app.routers import auth, patients, data_ingest

app = FastAPI(title="Authentication API")

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(data_ingest.router, prefix="/api/ingest", tags=["Data_Ingestion"])

@app.get("/")
def read_root():
    return {"message": "Auth Backend is running"}