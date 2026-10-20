"""Promote an existing user to admin (the only way to create admins):  python scripts/make_admin.py user@example.com"""
import sys; sys.path.insert(0, ".")
from sqlalchemy import select
from app.db import SessionLocal
from app.models import User
with SessionLocal() as db:
    u = db.scalar(select(User).where(User.email == sys.argv[1].lower()))
    if not u: sys.exit("User not found")
    u.role = "admin"; db.commit(); print("OK:", u.email, "is now admin")
