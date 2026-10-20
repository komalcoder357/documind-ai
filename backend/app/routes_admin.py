import os
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from . import config, llm, rag
from .db import get_db
from .deps import require_admin, audit
from .models import *

router = APIRouter(prefix="/api/v1/admin")

@router.get("/stats")
def stats(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    c = lambda q: db.scalar(q) or 0; since = now() - timedelta(days=7)
    done = list(db.execute(select(Job.started_at, Job.finished_at).where(Job.status == "succeeded", Job.finished_at.isnot(None), Job.started_at.isnot(None))))
    lat = [(aware(f) - aware(s)).total_seconds() for s, f in done]
    kinds = dict(db.execute(select(Job.kind, func.count(Job.id)).group_by(Job.kind)).all())
    return {"users_total": c(select(func.count(User.id))), "active_users_7d": c(select(func.count(func.distinct(AuditEvent.user_id))).where(AuditEvent.action == "login", AuditEvent.created_at >= since)),
            "workspaces": c(select(func.count(Workspace.id))), "documents_uploaded": c(select(func.count(Document.id))), "documents_processed": c(select(func.count(Document.id)).where(Document.status == "ready")),
            "failed_jobs": c(select(func.count(Job.id)).where(Job.status == "failed")), "cv_analyses_completed": c(select(func.count(Assessment.id))),
            "storage_bytes": c(select(func.sum(Document.size_bytes))), "avg_job_seconds": round(sum(lat) / len(lat), 3) if lat else None,
            "jobs_by_kind": kinds, "window": "active users = distinct users with a login in the last 7 days"}

@router.get("/users")
def users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "is_active": u.is_active, "created_at": u.created_at} for u in db.scalars(select(User).order_by(User.id).limit(200))]

@router.post("/users/{uid}/suspend")
def suspend(uid: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u: raise HTTPException(404, "User not found.")
    if u.id == admin.id: raise HTTPException(409, "You cannot suspend yourself.")
    u.is_active = False
    for s in db.scalars(select(AuthSession).where(AuthSession.user_id == uid)): db.delete(s)
    db.commit(); audit(db, admin.id, f"admin.suspend:{uid}"); return {"ok": True}

@router.post("/users/{uid}/reactivate")
def reactivate(uid: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u: raise HTTPException(404, "User not found.")
    u.is_active = True; db.commit(); audit(db, admin.id, f"admin.reactivate:{uid}"); return {"ok": True}

@router.get("/audit")
def audit_log(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [{"id": a.id, "user_id": a.user_id, "action": a.action, "created_at": a.created_at} for a in db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(200))]

@router.get("/health")
def service_health(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"database": "ok", "llm_provider": config.LLM_PROVIDER if llm.available() else "none (extractive fallback)", "embeddings": rag.embed_mode(),
            "job_runner": "synchronous" if config.JOBS_SYNC else "in-process thread pool", "ocr": "not configured"}
