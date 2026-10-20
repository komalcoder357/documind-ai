import logging, os
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import delete, select
from . import config, extract, rag
from .db import SessionLocal
from .models import Job, Document, Chunk, Candidate, now

log = logging.getLogger("documind.jobs")
_pool = ThreadPoolExecutor(max_workers=2)

class PermanentError(Exception): pass

from .jobs_util import stage

def process_document(db, job):
    d = db.get(Document, job.target_id)
    if not d: raise PermanentError("Document no longer exists.")
    try:
        d.status = "validating"; stage(db, job, "validating", 0, 5)
        with open(os.path.join(config.STORAGE_DIR, d.storage_key), "rb") as f: raw = f.read()
        kind = extract.sniff(raw, d.title)
        d.status = "extracting"; stage(db, job, "extracting", 1, 5)
        pages, warnings = extract.extract_pages(raw, kind, config.MAX_PAGES)
        d.status = "chunking"; stage(db, job, "chunking", 2, 5)
        pieces = rag.chunk_pages(pages)
        if not pieces: raise PermanentError("No text could be extracted from this document.")
        d.status = "embedding"; stage(db, job, "embedding", 3, 5)
        vecs = [rag.embed(p.text) for p in pieces]
        d.status = "indexing"; stage(db, job, "indexing", 4, 5)
        db.execute(delete(Chunk).where(Chunk.document_id == d.id))          # idempotent on retry
        db.add_all([Chunk(document_id=d.id, workspace_id=d.workspace_id, idx=i, page=p.page, heading=p.heading, text=p.text, embedding=v)
                    for i, (p, v) in enumerate(zip(pieces, vecs))])
        d.text_content = "\n\n".join((f"[Page {n}]\n" if n else "") + t for n, t in pages)
        d.warnings, d.page_count, d.error, d.status = warnings, len([1 for n, _ in pages if n]) or None, None, "ready"
        stage(db, job, "ready", 5, 5)
    except extract.ExtractError as e: raise PermanentError(str(e))

def fail_document(db, job, msg):
    d = db.get(Document, job.target_id)
    if d: d.status, d.error = "failed", msg

def process_candidate(db, job):
    from . import cv_pipeline
    cv_pipeline.run(db, job)

def fail_candidate(db, job, msg):
    c = db.get(Candidate, job.target_id)
    if c: c.status, c.error = "failed", msg

HANDLERS = {"document": (process_document, fail_document), "candidate": (process_candidate, fail_candidate)}

def run_job(job_id: int):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if not job or job.status != "queued": return
        run, fail = HANDLERS[job.kind]
        while True:
            job.status, job.attempts = "running", job.attempts + 1
            job.started_at = job.started_at or now(); job.error = None; db.commit()
            try:
                run(db, job); job.status = "succeeded"; break
            except PermanentError as e:
                db.rollback(); job = db.get(Job, job_id); job.status, job.error = "failed", str(e); fail(db, job, str(e)); break
            except Exception:
                db.rollback(); log.exception("job %s attempt %s failed", job_id, job.attempts)
                job = db.get(Job, job_id)
                if job.attempts >= config.MAX_JOB_ATTEMPTS:
                    msg = "Unexpected processing error. Please retry or contact support."
                    job.status, job.error = "failed", msg; fail(db, job, msg); break
        job.finished_at = now(); db.commit()

def enqueue(db, kind: str, target_id: int, ws: int) -> Job:
    job = Job(workspace_id=ws, kind=kind, target_id=target_id); db.add(job); db.commit()
    if config.JOBS_SYNC: run_job(job.id)
    else: _pool.submit(run_job, job.id)
    db.refresh(job); return job

def recover_abandoned():
    """On startup: jobs left 'running' by a crashed process are re-queued."""
    with SessionLocal() as db:
        ids = []
        for j in db.scalars(select(Job).where(Job.status.in_(["running", "queued"]))):
            j.status = "queued"; ids.append(j.id)
        db.commit()
    for i in ids: _pool.submit(run_job, i)
