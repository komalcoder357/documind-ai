import os, uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from . import config, extract, jobs, qa, docintel
from .db import get_db
from .deps import current_user, ws_ids, primary_ws, audit
from .models import *

router = APIRouter(prefix="/api/v1")

def doc_or_404(db, user, doc_id):
    d = db.get(Document, doc_id)
    if not d or d.workspace_id not in ws_ids(db, user): raise HTTPException(404, "Document not found.")
    return d

def job_out(j): return {"id": j.id, "kind": j.kind, "status": j.status, "stage": j.stage, "steps_done": j.steps_done, "steps_total": j.steps_total,
                        "progress_note": f"Step {j.steps_done} of {j.steps_total}", "attempts": j.attempts, "error": j.error,
                        "started_at": j.started_at, "finished_at": j.finished_at, "retry_available": j.status == "failed"}
def doc_out(d): return {"id": d.id, "title": d.title, "kind": d.kind, "status": d.status, "size_bytes": d.size_bytes, "page_count": d.page_count,
                        "warnings": d.warnings or [], "error": d.error, "created_at": d.created_at}

@router.post("/documents", status_code=201)
async def upload(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = os.path.basename(file.filename or "")[:255]
    raw = await file.read(config.MAX_UPLOAD + 1)
    if len(raw) > config.MAX_UPLOAD: raise HTTPException(413, "File too large.")
    try: kind = extract.sniff(raw, name)
    except extract.ExtractError as e: raise HTTPException(e.status, str(e))
    key = uuid.uuid4().hex
    os.makedirs(config.STORAGE_DIR, exist_ok=True)
    with open(os.path.join(config.STORAGE_DIR, key), "wb") as f: f.write(raw)
    ws = primary_ws(db, user)
    d = Document(workspace_id=ws, owner_id=user.id, title=name, kind=kind, storage_key=key, size_bytes=len(raw), status="queued"); db.add(d); db.commit()
    audit(db, user.id, "document.upload"); j = jobs.enqueue(db, "document", d.id, ws); db.refresh(d)
    return {**doc_out(d), "job": job_out(j)}

@router.get("/documents")
def list_docs(user: User = Depends(current_user), db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
    rows = db.scalars(select(Document).where(Document.workspace_id.in_(ws_ids(db, user))).order_by(Document.id.desc()).limit(min(limit, 100)).offset(offset))
    return [doc_out(d) for d in rows]

@router.get("/documents/{doc_id}")
def get_doc(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = doc_or_404(db, user, doc_id); return {**doc_out(d), "text": d.text_content}

@router.get("/documents/{doc_id}/status")
def status(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = doc_or_404(db, user, doc_id)
    j = db.scalar(select(Job).where(Job.kind == "document", Job.target_id == d.id).order_by(Job.id.desc()))
    return {"document": doc_out(d), "job": job_out(j) if j else None}

@router.get("/documents/{doc_id}/chunks")
def chunks(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = doc_or_404(db, user, doc_id)
    return [{"id": c.id, "idx": c.idx, "page": c.page, "heading": c.heading, "text": c.text} for c in db.scalars(select(Chunk).where(Chunk.document_id == d.id).order_by(Chunk.idx).limit(500))]

@router.get("/documents/{doc_id}/file")
def download(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = doc_or_404(db, user, doc_id)
    mt = {"pdf": "application/pdf", "txt": "text/plain", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}[d.kind]
    return FileResponse(os.path.join(config.STORAGE_DIR, d.storage_key), media_type=mt, filename=d.title, content_disposition_type="attachment" if d.kind != "pdf" else "inline")

@router.delete("/documents/{doc_id}")
def delete_doc(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = doc_or_404(db, user, doc_id)
    try: os.remove(os.path.join(config.STORAGE_DIR, d.storage_key))
    except FileNotFoundError: pass
    db.execute(delete(Job).where(Job.kind == "document", Job.target_id == d.id)); db.delete(d); db.commit()
    audit(db, user.id, "document.delete"); return {"ok": True}

# ---- jobs ----
@router.get("/jobs")
def list_jobs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [job_out(j) for j in db.scalars(select(Job).where(Job.workspace_id.in_(ws_ids(db, user))).order_by(Job.id.desc()).limit(30))]

def job_or_404(db, user, jid):
    j = db.get(Job, jid)
    if not j or j.workspace_id not in ws_ids(db, user): raise HTTPException(404, "Job not found.")
    return j

@router.get("/jobs/{jid}")
def get_job(jid: int, user: User = Depends(current_user), db: Session = Depends(get_db)): return job_out(job_or_404(db, user, jid))

@router.post("/jobs/{jid}/cancel")
def cancel(jid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    j = job_or_404(db, user, jid)
    if j.status != "queued": raise HTTPException(409, "Only queued jobs can be cancelled.")
    j.status = "cancelled"; db.commit(); return job_out(j)

@router.post("/jobs/{jid}/retry")
def retry(jid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    j = job_or_404(db, user, jid)
    if j.status != "failed": raise HTTPException(409, "Only failed jobs can be retried.")
    n = jobs.enqueue(db, j.kind, j.target_id, j.workspace_id); return job_out(n)

# ---- Q&A ----
class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000); doc_ids: list[int] | None = Field(None, max_length=10)
    conversation_id: int | None = None; top_k: int = Field(5, ge=1, le=10)

def _ask(db, user, ids, body):
    r = qa.answer_question(db, user, ws_ids(db, user), ids, body.question.strip(), body.conversation_id, body.top_k)
    if r is None: raise HTTPException(404, "No ready documents found in the selected scope.")
    if r == "bad_conversation": raise HTTPException(404, "Conversation not found.")
    return r

@router.post("/documents/{doc_id}/questions")
def ask_one(doc_id: int, body: AskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc_or_404(db, user, doc_id); return _ask(db, user, [doc_id], body)

@router.post("/qa")
def ask_many(body: AskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not body.doc_ids: raise HTTPException(422, "Select at least one document.")
    return _ask(db, user, body.doc_ids, body)

@router.get("/conversations")
def convs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": c.id, "title": c.title, "created_at": c.created_at} for c in db.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.id.desc()).limit(50))]

@router.get("/conversations/{cid}")
def conv(cid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(Conversation, cid)
    if not c or c.user_id != user.id: raise HTTPException(404, "Conversation not found.")
    return {"id": c.id, "messages": [{"role": m.role, "content": m.content, "meta": m.meta} for m in db.scalars(select(Message).where(Message.conversation_id == cid).order_by(Message.id))]}

@router.delete("/conversations/{cid}")
def del_conv(cid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(Conversation, cid)
    if not c or c.user_id != user.id: raise HTTPException(404, "Conversation not found.")
    db.delete(c); db.commit(); return {"ok": True}

# ---- document intelligence ----
@router.post("/documents/{doc_id}/summary")
def summary(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = doc_or_404(db, user, doc_id)
    if d.status != "ready": raise HTTPException(409, "Document is not ready yet.")
    return docintel.summarize(db, d)

class CompareIn(BaseModel): doc_ids: list[int] = Field(min_length=2, max_length=5)
def _ready_docs(db, user, ids):
    ds = [doc_or_404(db, user, i) for i in dict.fromkeys(ids)]
    if len(ds) < 1 or any(d.status != "ready" for d in ds): raise HTTPException(409, "All selected documents must be ready.")
    return ds

@router.post("/documents/compare")
def compare(body: CompareIn, user: User = Depends(current_user), db: Session = Depends(get_db)): return docintel.compare(db, _ready_docs(db, user, body.doc_ids))

class ResearchIn(BaseModel): doc_ids: list[int] = Field(min_length=1, max_length=5)
@router.post("/research/analyze")
def research(body: ResearchIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ds = _ready_docs(db, user, body.doc_ids)
    return {"papers": [{"document_id": d.id, "title": d.title, **docintel.research(db, d)} for d in ds], "gap_analysis": docintel.research_gaps(db, ds)}

@router.get("/evidence/{eid}")
def evidence(eid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .evidence import result_object
    e = db.get(Evidence, eid)
    if not e or e.workspace_id not in ws_ids(db, user): raise HTTPException(404, "Evidence not found.")
    return result_object(e)
