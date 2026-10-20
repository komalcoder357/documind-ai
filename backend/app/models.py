from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, UniqueConstraint, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def now(): return datetime.now(timezone.utc)
def aware(dt): return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)
CASC = dict(ondelete="CASCADE")
def ws_fk(): return mapped_column(ForeignKey("workspaces.id", **CASC), index=True)
def ts(): return mapped_column(DateTime(timezone=True), default=now)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    prefs: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = ts()

class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))

class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "workspace_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", **CASC), index=True)
    workspace_id: Mapped[int] = ws_fk()
    role: Mapped[str] = mapped_column(String(20), default="owner")

class AuthSession(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", **CASC), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", **CASC), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = ws_fk()
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", **CASC))
    title: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(10))
    storage_key: Mapped[str] = mapped_column(String(64), unique=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = ts()

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = ws_fk()
    kind: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(30), default="queued")
    steps_done: Mapped[int] = mapped_column(Integer, default=0)
    steps_total: Mapped[int] = mapped_column(Integer, default=1)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = ts()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("document_id", "idx"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", **CASC), index=True)
    workspace_id: Mapped[int] = ws_fk()
    idx: Mapped[int] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading: Mapped[str | None] = mapped_column(String(200), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSON)

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = ws_fk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", **CASC), index=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = ts()

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", **CASC), index=True)
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = ts()

class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = ws_fk()
    source_type: Mapped[str] = mapped_column(String(20))      # chunk | cv | repository | link
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    claim: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[str] = mapped_column(Text, default="")
    method: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), default="not_checked")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", **CASC), nullable=True, index=True)
    created_at: Mapped[datetime] = ts()

class RecruitProject(Base):
    __tablename__ = "recruit_projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = ws_fk()
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", **CASC))
    title: Mapped[str] = mapped_column(String(200))
    job_title: Mapped[str] = mapped_column(String(200))
    job_description: Mapped[str] = mapped_column(Text, default="")
    criteria: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = ts()

class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("recruit_projects.id", **CASC), index=True)
    workspace_id: Mapped[int] = ws_fk()
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    text: Mapped[str] = mapped_column(Text, default="")
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    portfolio: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = ts()

class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", **CASC), unique=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("recruit_projects.id", **CASC), index=True)
    overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    criteria: Mapped[list] = mapped_column(JSON, default=list)
    interview_questions: Mapped[list] = mapped_column(JSON, default=list)
    formula_version: Mapped[str] = mapped_column(String(20), default="v1")
    created_at: Mapped[datetime] = ts()

class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = ws_fk()
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", **CASC))
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = ts()

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = ts()
