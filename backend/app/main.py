import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from . import config
from .db import Base, engine, SessionLocal
from . import models  # noqa
from .routes_auth import router as auth_r
from .routes_docs import router as docs_r
from .routes_recruit import router as rec_r, rep as rep_r
from .routes_admin import router as admin_r

@asynccontextmanager
async def lifespan(app):
    if config.AUTO_CREATE_TABLES: Base.metadata.create_all(engine)
    os.makedirs(config.STORAGE_DIR, exist_ok=True)
    if not config.JOBS_SYNC:
        try:
            from .jobs import recover_abandoned; recover_abandoned()
        except Exception: pass
    yield

app = FastAPI(title="DocuMind AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token"])

@app.middleware("http")
async def security_headers(request: Request, call_next):
    r = await call_next(request)
    r.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer"})
    if not request.url.path.startswith(("/docs", "/redoc", "/openapi")):
        r.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return r

for r in (auth_r, docs_r, rec_r, rep_r, admin_r): app.include_router(r)

@app.get("/api/v1/health")
def health(): return {"status": "ok"}

@app.get("/api/v1/ready")
def ready():
    try:
        with SessionLocal() as db: db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse({"status": "database_unavailable"}, 503)
