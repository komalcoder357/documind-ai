from sqlalchemy import delete, select
from . import cv, github
from .evidence import add_evidence
from .models import Candidate, RecruitProject, Assessment, Evidence
from .jobs_util import stage

NOT_FETCHED = "Page was not fetched: LinkedIn and most portfolio sites require login or forbid automated access, and no authorized API is configured."

def run(db, job):
    c = db.get(Candidate, job.target_id); p = db.get(RecruitProject, c.project_id) if c else None
    if not c or not p:
        from .jobs import PermanentError; raise PermanentError("Candidate or project no longer exists.")
    c.status = "analyzing"; stage(db, job, "portfolio", 0, 3)
    links, portfolio = c.profile.get("links", {}), []
    if c.profile.get("_check_portfolio", True):
        portfolio += [github.inspect(u) for u in links.get("github", [])[:3]]
    else:
        portfolio += [{"url": u, "kind": "github", "status": "not_checked", "reason": "Portfolio check was disabled by the recruiter.", "repos": []} for u in links.get("github", [])[:3]]
    portfolio += [{"url": u, "kind": k, "status": "not_checked", "reason": NOT_FETCHED, "repos": []} for k in ("linkedin", "other") for u in links.get(k, [])[:3]]
    c.portfolio = portfolio; stage(db, job, "assessing", 1, 3)
    results, overall, cov = cv.assess(c.profile, c.text, p.criteria, portfolio)
    qs = cv.interview_questions(c.profile, results)
    db.execute(delete(Evidence).where(Evidence.source_id == c.id, Evidence.source_type.in_(["cv", "repository"])))
    for r in results:
        for e in r["evidence"]:
            add_evidence(db, c.workspace_id, e["source_type"], c.id, e["location"], f"{r['name']}: {r['status']}", e["excerpt"], "deterministic_rule_match", e["verification"], {"criterion_id": r["id"]})
    a = db.scalar(select(Assessment).where(Assessment.candidate_id == c.id)) or Assessment(candidate_id=c.id, project_id=p.id)
    a.overall, a.coverage, a.criteria, a.interview_questions = overall, cov, results, qs
    db.add(a); c.status = "analyzed"; c.error = None; stage(db, job, "done", 3, 3)
