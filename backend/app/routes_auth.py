import os, secrets
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from . import config
from .db import get_db
from .deps import *
from .models import *

router = APIRouter(prefix="/api/v1")

class RegisterIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=120); email: EmailStr
    password: str = Field(min_length=8, max_length=128); accept_terms: bool
class LoginIn(BaseModel): email: EmailStr; password: str = Field(max_length=128)
class ForgotIn(BaseModel): email: EmailStr
class ResetIn(BaseModel): token: str; password: str = Field(min_length=8, max_length=128)
class PrefsIn(BaseModel): onboarding_done: bool | None = None; theme: str | None = Field(None, pattern="^(light|dark)$"); reduced_motion: bool | None = None; walkthroughs_seen: list[str] | None = None
class DeleteMeIn(BaseModel): password: str

def pub(u): return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "prefs": u.prefs or {}}

@router.post("/auth/register", status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    throttle("reg:" + (request.client.host if request.client else "x"), 20, 3600)
    if not body.accept_terms: raise HTTPException(422, "You must accept the Terms of Use.")
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)): raise HTTPException(409, "Could not register with these details.")
    u = User(email=email, full_name=body.full_name.strip(), password_hash=hash_password(body.password), role="user", prefs={})   # role is never client-controlled
    db.add(u); db.flush()
    w = Workspace(name=f"{u.full_name}'s workspace"); db.add(w); db.flush()
    db.add(Membership(user_id=u.id, workspace_id=w.id, role="owner")); db.commit()
    audit(db, u.id, "register"); return pub(u)

@router.post("/auth/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower(); throttle("login:" + email)
    u = db.scalar(select(User).where(User.email == email))
    if not u or not u.is_active or not verify_password(body.password, u.password_hash): raise HTTPException(401, "Invalid email or password.")
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    db.add(AuthSession(token_hash=tok_hash(token), user_id=u.id, expires_at=now() + timedelta(days=config.SESSION_DAYS))); db.commit()
    age = config.SESSION_DAYS * 86400
    response.set_cookie("session", token, httponly=True, secure=config.COOKIE_SECURE, samesite="lax", max_age=age)
    response.set_cookie("csrf", csrf, httponly=False, secure=config.COOKIE_SECURE, samesite="lax", max_age=age)
    audit(db, u.id, "login"); return {**pub(u), "csrf_token": csrf}

@router.post("/auth/logout")
def logout(request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.scalar(select(AuthSession).where(AuthSession.token_hash == tok_hash(request.cookies["session"])))
    if s: db.delete(s); db.commit()
    response.delete_cookie("session"); response.delete_cookie("csrf"); return {"ok": True}

@router.get("/auth/me")
def me(user: User = Depends(current_user)): return pub(user)

@router.post("/auth/forgot-password")
def forgot(body: ForgotIn, db: Session = Depends(get_db)):
    throttle("forgot:" + body.email.lower(), 3, 3600)
    u = db.scalar(select(User).where(User.email == body.email.lower())); out = {"message": "If that account exists, a reset link has been sent."}
    if u:
        t = secrets.token_urlsafe(32)
        db.add(PasswordReset(token_hash=tok_hash(t), user_id=u.id, expires_at=now() + timedelta(minutes=30))); db.commit()
        # Email delivery is not configured in this build; the token is never logged. Local development can opt in to receiving it.
        if config.DEV_RETURN_RESET_TOKEN: out["dev_token"] = t
    return out

@router.post("/auth/reset-password")
def reset(body: ResetIn, db: Session = Depends(get_db)):
    r = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == tok_hash(body.token)))
    if not r or r.used or aware(r.expires_at) < now(): raise HTTPException(400, "Invalid or expired reset link.")
    u = db.get(User, r.user_id); u.password_hash = hash_password(body.password); r.used = True
    for s in db.scalars(select(AuthSession).where(AuthSession.user_id == u.id)): db.delete(s)   # invalidate sessions
    db.commit(); audit(db, u.id, "password.reset"); return {"ok": True}

@router.put("/me/preferences")
def prefs(body: PrefsIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = dict(user.prefs or {}); p.update({k: v for k, v in body.model_dump().items() if v is not None}); user.prefs = p; db.commit(); return pub(user)

@router.delete("/me")
def delete_me(body: DeleteMeIn, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.password, user.password_hash): raise HTTPException(403, "Password incorrect.")
    ws = ws_ids(db, user)
    keys = list(db.scalars(select(Document.storage_key).where(Document.workspace_id.in_(ws)))) + list(db.scalars(select(Candidate.storage_key).where(Candidate.workspace_id.in_(ws))))
    for k in keys:
        try: os.remove(os.path.join(config.STORAGE_DIR, k))
        except FileNotFoundError: pass
    uid = user.id
    for w in ws: db.delete(db.get(Workspace, w))
    db.flush(); db.delete(db.get(User, uid)); db.commit(); audit(db, None, f"user.deleted:{uid}")
    response.delete_cookie("session"); response.delete_cookie("csrf"); return {"ok": True}

@router.get("/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    ws = ws_ids(db, user); cnt = lambda q: db.scalar(q) or 0
    D = Document.workspace_id.in_(ws)
    docs = db.scalars(select(Document).where(D).order_by(Document.id.desc()).limit(5))
    projs = db.scalars(select(RecruitProject).where(RecruitProject.workspace_id.in_(ws)).order_by(RecruitProject.id.desc()).limit(5))
    return {"documents_total": cnt(select(func.count(Document.id)).where(D)), "documents_ready": cnt(select(func.count(Document.id)).where(D, Document.status == "ready")),
            "documents_pending": cnt(select(func.count(Document.id)).where(D, Document.status.notin_(["ready", "failed"]))),
            "cvs_analyzed": cnt(select(func.count(Candidate.id)).where(Candidate.workspace_id.in_(ws), Candidate.status == "analyzed")),
            "storage_bytes": cnt(select(func.sum(Document.size_bytes)).where(D)),
            "recent_documents": [{"id": d.id, "title": d.title, "status": d.status} for d in docs],
            "recent_projects": [{"id": p.id, "title": p.title, "job_title": p.job_title} for p in projs],
            "running_jobs": cnt(select(func.count(Job.id)).where(Job.workspace_id.in_(ws), Job.status.in_(["queued", "running"])))}
