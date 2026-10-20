from conftest import make_pdf, make_docx
from app.db import SessionLocal
from app.models import Chunk, Job, Document
from app import jobs
from sqlalchemy import select, func

TXT = ("INTRODUCTION\nThe river basin study examines flood risk in the northern valley. " * 3).encode()

def test_txt_pdf_docx_processing_and_status(user):
    for name, data in [("a.txt", TXT), ("b.pdf", make_pdf(["Page one about solar energy panels and grid storage.", "Page two about wind turbines and offshore farms."])),
                       ("c.docx", make_docx(["Heading text here", "Paragraph about hydrogen fuel cells and electrolysis processes."]))]:
        r = user.upload(name, data); assert r.status_code == 201, r.text
        assert r.json()["status"] == "ready" and r.json()["job"]["status"] == "succeeded" and r.json()["job"]["steps_done"] == 5
    docs = user.get("/api/v1/documents").json(); assert len(docs) == 3
    pdf = next(d for d in docs if d["kind"] == "pdf"); assert pdf["page_count"] == 2
    ch = user.get(f"/api/v1/documents/{pdf['id']}/chunks").json(); assert {c["page"] for c in ch} == {1, 2}

def test_rejects_bad_files(user):
    assert user.upload("x.exe", b"MZ....").status_code == 415
    assert user.upload("fake.pdf", b"not a pdf at all").status_code == 415
    assert user.upload("fake.docx", b"PK-not-really").status_code == 415
    assert user.upload("e.txt", b"   ").status_code == 422
    assert user.upload("bin.txt", b"abc\x00def").status_code == 415
    assert user.upload("enc.pdf", make_pdf(["secret text here for pdf"], password="pw")).status_code == 415
    assert user.upload("../../evil.txt", TXT).json()["title"] == "evil.txt"

def test_scanned_pdf_reports_ocr_needed(user):
    import pymupdf
    d = pymupdf.open(); d.new_page(); d.new_page()
    r = user.upload("scan.pdf", d.tobytes())
    assert r.status_code == 201 and r.json()["status"] == "failed" and "OCR" in r.json()["error"]

def test_isolation_between_users(user, user2):
    did = user.upload("a.txt", TXT).json()["id"]
    for path in (f"/api/v1/documents/{did}", f"/api/v1/documents/{did}/status", f"/api/v1/documents/{did}/chunks", f"/api/v1/documents/{did}/file"):
        assert user2.get(path).status_code == 404
    assert user2.delete(f"/api/v1/documents/{did}").status_code == 404
    assert user2.post(f"/api/v1/documents/{did}/questions", json={"question": "flood risk?"}).status_code == 404
    assert user2.get("/api/v1/documents").json() == []

def test_retry_is_idempotent_no_duplicate_chunks(user):
    did = user.upload("a.txt", TXT * 20).json()["id"]
    with SessionLocal() as db:
        n1 = db.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == did)); ws = db.get(Document, did).workspace_id
        for _ in range(2): j = jobs.enqueue(db, "document", did, ws)
        assert db.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == did)) == n1 > 0

def test_failed_job_retry_endpoint(user):
    did = user.upload("a.txt", TXT).json()["id"]
    import os; from app import config
    with SessionLocal() as db: d = db.get(Document, did); key = d.storage_key
    os.rename(os.path.join(config.STORAGE_DIR, key), os.path.join(config.STORAGE_DIR, key + ".bak"))
    st = user.get(f"/api/v1/documents/{did}/status").json()
    with SessionLocal() as db: ws = db.get(Document, did).workspace_id; j = jobs.enqueue(db, "document", did, ws); jid = j.id
    assert user.get(f"/api/v1/jobs/{jid}").json()["status"] == "failed"
    os.rename(os.path.join(config.STORAGE_DIR, key + ".bak"), os.path.join(config.STORAGE_DIR, key))
    r = user.post(f"/api/v1/jobs/{jid}/retry"); assert r.json()["status"] == "succeeded"

def test_delete_removes_chunks_and_file(user):
    did = user.upload("a.txt", TXT).json()["id"]
    assert user.delete(f"/api/v1/documents/{did}").status_code == 200
    with SessionLocal() as db: assert db.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == did)) == 0
