import io
from conftest import make_pdf, make_docx
from app import github, cv
from app.db import SessionLocal
from app.models import Evidence

CV_A = """Ayesha Khan
ayesha@example.com  +92 300 1234567
https://github.com/ayeshak  https://www.linkedin.com/in/ayeshak
EDUCATION
BSCS, Government College University, 2019 - 2023
SKILLS
Python, Machine Learning, SQL, Docker
EXPERIENCE
Data Analyst, Acme 2021 - 2024
Built Python pipelines.
PROJECTS
Flood prediction system using Python and scikit-learn
"""
CV_B = """Bilal Ahmed
bilal@example.com
SKILLS
Java, Spring
EXPERIENCE
Developer 2022 - 2023
"""

def mk_project(user, **kw):
    body = {"title": "Hiring", "job_title": "ML Engineer", "job_description": "ML role", "required_skills": ["Python", "Machine Learning", "Rust"], "preferred_skills": ["Docker"], "min_years": 2, "education": "bachelor", **kw}
    r = user.post("/api/v1/recruitment/projects", json=body); assert r.status_code == 201, r.text; return r.json()

def upload_cvs(user, pid, items):
    files = [("files", (n, d)) for n, d in items]
    r = user.post(f"/api/v1/recruitment/projects/{pid}/candidates", files=files); assert r.status_code == 201, r.text; return r.json()["results"]

def fake_gh(monkeypatch, repo_langs=None, status=200):
    def fj(path):
        if path.startswith("/users/"): return status, [{"name": "ml-repo"}]
        if path.endswith("/languages"): return status, repo_langs or {"Python": 9000, "Jupyter Notebook": 1000}
        if path.endswith("/readme"):
            import base64; return status, {"content": base64.b64encode(b"Flood model with Docker support and pytest tests.").decode()}
        if "/git/trees/" in path: return status, {"tree": [{"path": "tests/test_a.py"}, {"path": "docs/index.md"}]}
        return status, {"description": "demo", "fork": False, "topics": ["ml"], "default_branch": "main"}
    monkeypatch.setattr(github, "fetch_json", fj)

def test_criteria_scoring_and_missing_evidence(user, monkeypatch):
    fake_gh(monkeypatch); p = mk_project(user)
    res = upload_cvs(user, p["id"], [("a.txt", CV_A.encode()), ("b.docx", make_docx(CV_B.splitlines()))]); assert all(r["status"] == "uploaded" for r in res)
    assert user.post(f"/api/v1/recruitment/projects/{p['id']}/analyze", json={"check_portfolio": True}).status_code == 200
    out = user.get(f"/api/v1/recruitment/projects/{p['id']}/results").json()
    assert "human review" in out["disclaimer"] and out["candidates"][0]["overall"] > out["candidates"][1]["overall"]
    a = out["candidates"][0]; by = {c["name"]: c for c in a["criteria"]}
    assert by["Python"]["status"] == "supported_by_work_sample"       # CV + repo language evidence
    assert by["Docker"]["status"] == "supported_by_work_sample"       # via README
    assert by["Rust"]["status"] == "not_found" and by["Rust"]["value"] is None        # missing != zero
    assert a["overall"] < 100 and a["coverage"] < 100                 # no artificially perfect score
    assert any(l["kind"] == "linkedin" and l["status"] == "not_checked" for l in a["portfolio"])
    b = out["candidates"][1]; assert {c["name"]: c for c in b["criteria"]}["Python"]["status"] == "not_found"

def test_score_formula_is_reproducible():
    crit = cv.build_criteria(["Python", "Rust"], [], None, None)
    prof = cv.parse_cv(CV_A); res, overall, cov = cv.assess(prof, CV_A, crit, [])
    assert overall == round(100 * (3 * 0.8) / 6, 1) == 40.0 and cov == 50.0
    assert cv.assess(prof, CV_A, crit, [])[1] == overall

def test_no_protected_traits_in_scoring():
    a = CV_A; b = CV_A.replace("Ayesha Khan", "John Smith").replace("ayesha", "john")
    crit = cv.build_criteria(["Python", "SQL"], [], 2, "bachelor")
    assert cv.assess(cv.parse_cv(a), a, crit, [])[1] == cv.assess(cv.parse_cv(b), b, crit, [])[1]

def test_experience_education_statuses():
    prof = cv.parse_cv(CV_A); crit = cv.build_criteria([], [], 5, "master")
    res, _, _ = cv.assess(prof, CV_A, crit, [])
    assert [r["status"] for r in res] == ["partial", "partial"]
    res2, o, c = cv.assess(cv.parse_cv("Just a name\nno details"), "Just a name\nno details", crit, [])
    assert [r["status"] for r in res2] == ["unable_to_verify", "not_found"] and c == 0.0

def test_github_rate_limit_and_unavailable(user, monkeypatch):
    fake_gh(monkeypatch, status=403); p = mk_project(user)
    upload_cvs(user, p["id"], [("a.txt", CV_A.encode())]); user.post(f"/api/v1/recruitment/projects/{p['id']}/analyze", json={})
    gh = [l for l in user.get(f"/api/v1/recruitment/projects/{p['id']}/results").json()["candidates"][0]["portfolio"] if l["kind"] == "github"][0]
    assert gh["status"] == "rate_limited"
    def net(path): raise ConnectionError("down")
    monkeypatch.setattr(github, "fetch_json", net); assert github.inspect("https://github.com/x/y")["status"] == "unavailable"
    assert github.inspect("https://evil.com/github.com/x")["status"] == "not_checked"
    assert github.parse("https://github.com/a/b.git") == ("a", "b") and github.parse("https://github.com.evil.com/a") is None

def test_portfolio_check_can_be_disabled(user, monkeypatch):
    calls = []; monkeypatch.setattr(github, "fetch_json", lambda p: calls.append(p) or (200, {}))
    p = mk_project(user); upload_cvs(user, p["id"], [("a.txt", CV_A.encode())]); user.post(f"/api/v1/recruitment/projects/{p['id']}/analyze", json={"check_portfolio": False})
    assert calls == []

def test_bulk_upload_validation_per_file(user):
    p = mk_project(user)
    res = upload_cvs(user, p["id"], [("ok.txt", CV_A.encode()), ("bad.exe", b"MZ"), ("empty.txt", b"  "), ("fake.pdf", b"nope")])
    assert [r["status"] for r in res] == ["uploaded", "rejected", "rejected", "rejected"] and all("error" in r for r in res[1:])

def test_report_questions_evidence_and_export(user, monkeypatch):
    fake_gh(monkeypatch); p = mk_project(user)
    cid = upload_cvs(user, p["id"], [("a.pdf", make_pdf(CV_A.split("\n\n")))])[0]["id"]
    assert user.get(f"/api/v1/recruitment/candidates/{cid}/report").status_code == 409
    user.post(f"/api/v1/recruitment/projects/{p['id']}/analyze", json={})
    r = user.get(f"/api/v1/recruitment/candidates/{cid}/report").json()
    assert r["missing_or_uncertain"] and r["interview_questions"] and r["limitations"] and r["evaluated_at"]
    q = next(q for q in r["interview_questions"] if q["skill"] == "Rust"); assert "does not mention" in q["question"] and q["evidence_ref"] is None and q["rubric"]
    assert user.post(f"/api/v1/recruitment/candidates/{cid}/interview-questions").json()["questions"]
    with SessionLocal() as db: assert db.query(Evidence).filter(Evidence.source_type == "cv", Evidence.source_id == cid, Evidence.status == "supported").count() > 0
    rid = user.post(f"/api/v1/recruitment/projects/{p['id']}/export").json()["report_id"]
    csv_ = user.get(f"/api/v1/reports/{rid}/download?format=csv"); assert csv_.status_code == 200 and "overall_match_score" in csv_.text
    dx = user.get(f"/api/v1/reports/{rid}/download?format=docx"); assert dx.content[:2] == b"PK"
    assert len(user.get("/api/v1/reports").json()) == 1 and user.delete(f"/api/v1/reports/{rid}").status_code == 200

def test_recruitment_isolation_and_validation(user, user2):
    p = mk_project(user); cid = upload_cvs(user, p["id"], [("a.txt", CV_A.encode())])[0]["id"]
    for path in (f"/api/v1/recruitment/projects/{p['id']}", f"/api/v1/recruitment/projects/{p['id']}/results", f"/api/v1/recruitment/candidates/{cid}/report"):
        assert user2.get(path).status_code == 404
    assert user2.post(f"/api/v1/recruitment/projects/{p['id']}/analyze", json={}).status_code == 404
    assert user2.post(f"/api/v1/recruitment/projects/{p['id']}/criteria", json=[{"type": "skill", "target": "x", "weight": 1}]).status_code == 404
    assert user.post(f"/api/v1/recruitment/projects/{p['id']}/criteria", json=[]).status_code == 422
    assert user.post(f"/api/v1/recruitment/projects/{p['id']}/criteria", json=[{"type": "skill", "target": "x", "weight": 0}]).status_code == 422
    edited = user.post(f"/api/v1/recruitment/projects/{p['id']}/criteria", json=[{"type": "skill", "target": "Go", "weight": 5}]).json(); assert edited["criteria"][0]["weight"] == 5
    assert user.post("/api/v1/recruitment/projects", json={"title": "t", "job_title": "j", "education": "wizard"}).status_code == 422

def test_analyze_requires_cvs_and_criteria(user):
    p = mk_project(user); assert user.post(f"/api/v1/recruitment/projects/{p['id']}/analyze", json={}).status_code == 422
