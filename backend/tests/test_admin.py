from fastapi.testclient import TestClient
from conftest import Client
from app.db import SessionLocal
from app.models import User

def make_admin(c):
    with SessionLocal() as db: db.query(User).filter(User.email == c.email).one().role = "admin"; db.commit()

def test_user_cannot_access_admin(user):
    for p in ("/api/v1/admin/stats", "/api/v1/admin/users", "/api/v1/admin/audit", "/api/v1/admin/health"): assert user.get(p).status_code == 403
    assert TestClient(__import__("app.main", fromlist=["app"]).app).get("/api/v1/admin/stats").status_code == 401

def test_admin_stats_are_real_and_safe(user):
    user.upload("a.txt", b"hello world text for stats " * 5); adm = Client(); make_admin(adm)
    s = adm.get("/api/v1/admin/stats").json()
    assert s["documents_uploaded"] >= 1 and s["users_total"] >= 2 and s["storage_bytes"] > 0 and s["active_users_7d"] >= 1
    assert "password" not in adm.get("/api/v1/admin/users").text.lower()
    assert adm.get("/api/v1/admin/health").json()["database"] == "ok"

def test_suspend_blocks_login_and_is_audited(user):
    adm = Client(); make_admin(adm); uid = user.get("/api/v1/auth/me").json()["id"]
    assert adm.post(f"/api/v1/admin/users/{uid}/suspend").status_code == 200
    assert user.get("/api/v1/auth/me").status_code == 401
    assert TestClient(__import__("app.main", fromlist=["app"]).app).post("/api/v1/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}).status_code == 401
    assert any(a["action"] == f"admin.suspend:{uid}" for a in adm.get("/api/v1/admin/audit").json())
    adm.post(f"/api/v1/admin/users/{uid}/reactivate")
    assert adm.post(f"/api/v1/admin/users/{adm.get('/api/v1/auth/me').json()['id']}/suspend").status_code == 409

def test_health_ready_and_headers(user):
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    assert c.get("/api/v1/health").json()["status"] == "ok" and c.get("/api/v1/ready").json()["status"] == "ready"
    assert c.get("/api/v1/health").headers["x-content-type-options"] == "nosniff"
