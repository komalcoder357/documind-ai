"""Shared Evidence Intelligence Engine: deterministic checks, independent of any LLM."""
import re
from sqlalchemy.orm import Session
from .models import Chunk, Evidence

STATES = ("supported", "contradicted", "insufficient_evidence", "not_checked", "verification_failed")
_norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()

def validate_citation(db: Session, ws: list[int], chunk_id: int, document_id: int, page):
    c = db.get(Chunk, chunk_id)
    if not c: return False, "chunk_not_found"
    if c.workspace_id not in ws: return False, "not_authorized"
    if c.document_id != document_id: return False, "document_mismatch"
    if c.page != page: return False, "page_mismatch"
    return True, "ok"

def verify_excerpt(excerpt: str, source_text: str) -> str:
    """Deterministic: does the quoted excerpt literally occur in the source?"""
    if not excerpt or not source_text: return "verification_failed"
    return "supported" if _norm(excerpt) in _norm(source_text) else "verification_failed"

def add_evidence(db: Session, ws: int, source_type: str, source_id, location, claim, excerpt, method, status="not_checked", details=None, message_id=None):
    assert status in STATES
    e = Evidence(workspace_id=ws, source_type=source_type, source_id=source_id, location=location, claim=claim[:2000], excerpt=excerpt[:2000],
                 method=method, status=status, details=details or {}, message_id=message_id)
    db.add(e); db.flush(); return e

def result_object(e: Evidence):
    return {"id": e.id, "claim": e.claim, "source_type": e.source_type, "source_id": e.source_id, "location": e.location,
            "excerpt": e.excerpt, "status": e.status, "method": e.method, "details": e.details, "timestamp": e.created_at.isoformat() if e.created_at else None}
