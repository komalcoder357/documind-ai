from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

@event.listens_for(Engine, "connect")
def _fk(conn, _):
    if DATABASE_URL.startswith("sqlite"):
        cur = conn.cursor(); cur.execute("PRAGMA foreign_keys=ON"); cur.close()

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
