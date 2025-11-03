# backend/app/main.py
from fastapi import FastAPI
from app.routers import auth, patients, data_ingest, recommendations # <--- Убедитесь, что 'recommendations' импортирован

app = FastAPI(title="Medical App API")

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(data_ingest.router, prefix="/api/ingest", tags=["Data Ingestion"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recommendations"]) # <--- Убедитесь, что эта строка есть

# ...

@app.get("/")
def read_root():
    return {"message": "Auth Backend is running"}