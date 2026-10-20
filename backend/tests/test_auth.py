from conftest import Client
from fastapi.testclient import TestClient
from app.main import app

def test_register_login_logout_flow(user):
    assert user.get("/api/v1/auth/me").json()["email"] == user.email
    assert user.post("/api/v1/auth/logout").status_code == 200
    assert user.get("/api/v1/auth/me").status_code == 401

def test_invalid_credentials_generic(user):
    c = TestClient(app)
    a = c.post("/api/v1/auth/login", json={"email": user.email, "password": "wrongpass1"})
    b = c.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrongpass1"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()

def test_duplicate_weak_and_terms():
    c = TestClient(app); base = {"full_name": "T", "email": "dup@example.com", "password": "Str0ngPassw0rd", "accept_terms": True}
    assert c.post("/api/v1/auth/register", json=base).status_code == 201
    assert c.post("/api/v1/auth/register", json=base).status_code == 409
    assert c.post("/api/v1/auth/register", json={**base, "email": "w@example.com", "password": "short"}).status_code == 422
    assert c.post("/api/v1/auth/register", json={**base, "email": "t@example.com", "accept_terms": False}).status_code == 422

def test_cannot_self_grant_admin():
    c = TestClient(app)
    r = c.post("/api/v1/auth/register", json={"full_name": "T", "email": "adm@example.com", "password": "Str0ngPassw0rd", "accept_terms": True, "role": "admin"})
    assert r.status_code == 201 and r.json()["role"] == "user"

def test_csrf_required(user):
    assert user.c.post("/api/v1/documents", files={"file": ("a.txt", b"hello world")}).status_code == 403

def test_login_throttle():
    c = TestClient(app); codes = [c.post("/api/v1/auth/login", json={"email": "thr@example.com", "password": "x" * 9}).status_code for _ in range(7)]
    assert 429 in codes

def test_password_reset_single_use_and_expiry(user):
    c = TestClient(app)
    t = c.post("/api/v1/auth/forgot-password", json={"email": user.email}).json()["dev_token"]
    assert c.post("/api/v1/auth/reset-password", json={"token": t, "password": "NewStr0ngPass1"}).status_code == 200
    assert c.post("/api/v1/auth/reset-password", json={"token": t, "password": "Another0Pass12"}).status_code == 400   # single use
    assert user.get("/api/v1/auth/me").status_code == 401                                                            # sessions invalidated
    assert c.post("/api/v1/auth/login", json={"email": user.email, "password": "NewStr0ngPass1"}).status_code == 200
    assert "dev_token" not in c.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"}).json()

def test_expired_reset_token(user):
    from app.db import SessionLocal; from app.models import PasswordReset, now; from datetime import timedelta
    c = TestClient(app); t = c.post("/api/v1/auth/forgot-password", json={"email": user.email}).json()["dev_token"]
    with SessionLocal() as db:
        for r in db.query(PasswordReset).all(): r.expires_at = now() - timedelta(minutes=1)
        db.commit()
    assert c.post("/api/v1/auth/reset-password", json={"token": t, "password": "NewStr0ngPass1"}).status_code == 400

def test_prefs_and_account_deletion(user):
    assert user.put("/api/v1/me/preferences", json={"onboarding_done": True}).json()["prefs"]["onboarding_done"] is True
    user.upload("a.txt", b"some text for deletion test " * 5)
    assert user.delete("/api/v1/me", json={"password": "wrong"}).status_code == 403
    assert user.delete("/api/v1/me", json={"password": "Str0ngPassw0rd"}).status_code == 200
    assert TestClient(app).post("/api/v1/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}).status_code == 401
