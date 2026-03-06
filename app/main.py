# backend/app/main.py
import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import Response
from app.routers import auth, patients, data_ingest, recommendations, simulator # <--- Убедитесь, что 'recommendations' импортирован

app = FastAPI(title="Medical App API")
logger = logging.getLogger("app.http")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(_handler)
logger.propagate = False


def _format_body(body: bytes) -> str:
    if body is None:
        return ""
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return repr(body)


@app.middleware("http")
async def log_http_traffic(request: Request, call_next):
    started_at = time.perf_counter()

    request_body = await request.body()

    async def receive():
        return {"type": "http.request", "body": request_body, "more_body": False}

    request = Request(request.scope, receive)

    logger.info(
        "[incoming request]\nmethod=%s\nurl=%s\nheaders=%s\nbody=%s",
        request.method,
        str(request.url),
        dict(request.headers),
        _format_body(request_body),
    )

    response = await call_next(request)

    response_chunks = [chunk async for chunk in response.body_iterator]
    response_body = b"".join(response_chunks)
    elapsed_ms = (time.perf_counter() - started_at) * 1000

    logger.info(
        "[outgoing response]\nmethod=%s\nurl=%s\nstatus_code=%s\nlatency_ms=%.2f\nheaders=%s\nbody=%s",
        request.method,
        str(request.url),
        response.status_code,
        elapsed_ms,
        dict(response.headers),
        _format_body(response_body),
    )

    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
        background=response.background,
    )

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
