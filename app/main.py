# backend/app/main.py
from fastapi import FastAPI, Request
from app.routers import auth, patients, data_ingest, recommendations, simulator # <--- Убедитесь, что 'recommendations' импортирован

app = FastAPI(title="Medical App API")


@app.middleware("http")
async def log_authorization_header(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        authorization = request.headers.get("authorization")
        print(
            f"[request] {request.method} {request.url.path} "
            f"authorization_present={authorization is not None} "
            f"authorization_prefix={authorization[:32] if authorization else None}"
        )

    response = await call_next(request)
    return response

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(data_ingest.router, prefix="/api/ingest", tags=["Data Ingestion"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recommendations"]) # <--- Убедитесь, что эта строка есть
app.include_router(simulator.router, prefix="/api/simulator", tags=["Simulator"])

# ...

@app.get("/")
def read_root():
    return {"message": "Auth Backend is running"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
