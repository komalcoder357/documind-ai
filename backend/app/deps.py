import hashlib, hmac, secrets
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import User, AuthSession, Membership, AuditEvent, now, aware

def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    return salt.hex() + ":" + hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1).hex()

def verify_password(pw: str, stored: str) -> bool:
    try:
        s, h = stored.split(":")
        return hmac.compare_digest(hashlib.scrypt(pw.encode(), salt=bytes.fromhex(s), n=2**14, r=8, p=1).hex(), h)
    except Exception:
        return False

def tok_hash(t: str) -> str: return hashlib.sha256(t.encode()).hexdigest()

_hits: dict[str, list] = {}
def throttle(key: str, limit=5, window=300):
    t = now().timestamp()
    h = [x for x in _hits.get(key, []) if t - x < window]
    if len(h) >= limit: raise HTTPException(429, "Too many attempts. Try again later.")
    _hits[key] = h + [t]

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("session")
    if not token: raise HTTPException(401, "Not authenticated")
    s = db.scalar(select(AuthSession).where(AuthSession.token_hash == tok_hash(token)))
    if not s or aware(s.expires_at) < now(): raise HTTPException(401, "Session expired")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        c, h = request.cookies.get("csrf"), request.headers.get("x-csrf-token")
        if not c or not h or not hmac.compare_digest(c, h): raise HTTPException(403, "CSRF check failed")
    u = db.get(User, s.user_id)
    if not u or not u.is_active: raise HTTPException(401, "Account unavailable")
    return u

def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin": raise HTTPException(403, "Administrator access required")
    return user

def ws_ids(db: Session, user: User) -> list[int]:
    return list(db.scalars(select(Membership.workspace_id).where(Membership.user_id == user.id)))

def primary_ws(db: Session, user: User) -> int: return ws_ids(db, user)[0]

def audit(db: Session, user_id, action: str):
    db.add(AuditEvent(user_id=user_id, action=action)); db.commit()
