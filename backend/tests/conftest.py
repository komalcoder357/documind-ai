import os, tempfile
_d = tempfile.mkdtemp()
os.environ.update(DATABASE_URL="sqlite:///" + os.path.join(_d, "t.db"), STORAGE_DIR=os.path.join(_d, "s"), JOBS_SYNC="true",
                  AUTO_CREATE_TABLES="true", DEV_RETURN_RESET_TOKEN="true", LLM_PROVIDER="none")
import io, itertools, pytest, pymupdf, docx
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine
from app import deps

Base.metadata.create_all(engine)
_n = itertools.count(1)

class Client:
    def __init__(self, email=None):
        self.c = TestClient(app); self.email = email or f"u{next(_n)}@example.com"; self.h = {}
        assert self.c.post("/api/v1/auth/register", json={"full_name": "Test User", "email": self.email, "password": "Str0ngPassw0rd", "accept_terms": True}).status_code == 201
        r = self.c.post("/api/v1/auth/login", json={"email": self.email, "password": "Str0ngPassw0rd"}); assert r.status_code == 200
        self.h = {"X-CSRF-Token": r.json()["csrf_token"]}
    def get(self, *a, **k): return self.c.get(*a, **k)
    def post(self, *a, **k): return self.c.post(*a, headers=self.h, **k)
    def put(self, *a, **k): return self.c.put(*a, headers=self.h, **k)
    def delete(self, url, **k): return self.c.request("DELETE", url, headers=self.h, **k)
    def upload(self, name, data): return self.post("/api/v1/documents", files={"file": (name, data)})

@pytest.fixture
def user(): deps._hits.clear(); return Client()
@pytest.fixture
def user2(): return Client()

def make_pdf(pages, password=None):
    d = pymupdf.open()
    for t in pages:
        p = d.new_page(); p.insert_textbox(pymupdf.Rect(50, 50, 550, 780), t, fontsize=11)
    return d.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password) if password else d.tobytes()

def make_docx(paras):
    d = docx.Document()
    for p in paras: d.add_paragraph(p)
    b = io.BytesIO(); d.save(b); return b.getvalue()
