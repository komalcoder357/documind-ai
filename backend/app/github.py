import base64, re
from datetime import datetime, timezone
import httpx
from . import config

GH = re.compile(r"^https?://(?:www\.)?github\.com/([A-Za-z0-9-]{1,39})(?:/([A-Za-z0-9._-]{1,100}))?/?(?:[#?].*)?$")
def parse(url: str):
    m = GH.match(url.strip()); return (m.group(1), (m.group(2) or "").removesuffix(".git") or None) if m else None

def fetch_json(path: str):
    h = {"Accept": "application/vnd.github+json", "User-Agent": "DocuMind-AI"}
    if config.GITHUB_TOKEN: h["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    r = httpx.get("https://api.github.com" + path, headers=h, timeout=8)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else None)

class _Limited(Exception): pass
def _get(path):
    s, d = fetch_json(path)
    if s in (403, 429): raise _Limited()
    return s, d

def _repo(u, name):
    s, meta = _get(f"/repos/{u}/{name}")
    if s != 200: return {"name": name, "status": "unavailable", "reason": f"GitHub API returned {s}"}
    _, langs = _get(f"/repos/{u}/{name}/languages"); langs = langs or {}
    tot = sum(langs.values()) or 1
    rs, rd = _get(f"/repos/{u}/{name}/readme"); readme = ""
    if rs == 200 and rd:
        try: readme = base64.b64decode(rd.get("content", "")).decode("utf-8", "ignore")[:3000]
        except Exception: pass
    paths = []
    ts, td = _get(f"/repos/{u}/{name}/git/trees/{meta.get('default_branch', 'HEAD')}?recursive=1")
    if ts == 200 and td: paths = [t["path"] for t in td.get("tree", [])][:2000]
    return {"name": name, "status": "checked", "description": meta.get("description"), "fork": bool(meta.get("fork")), "topics": meta.get("topics", []),
            "languages": {k: round(100 * v / tot, 1) for k, v in langs.items()}, "has_readme": bool(readme), "readme_excerpt": readme[:600],
            "readme_text": readme, "has_tests": any(re.search(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*\.py$|\.(test|spec)\.[jt]sx?$", p) for p in paths),
            "has_docs": any(p.lower().startswith("docs/") for p in paths), "file_count_sampled": len(paths)}

def inspect(url: str):
    """Official-API inspection of public GitHub data. Never clones or executes code."""
    base = {"url": url, "kind": "github", "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "notes": ["Public metadata does not prove the candidate wrote the code; commit counts and stars are not quality measures."]}
    p = parse(url)
    if not p: return {**base, "status": "not_checked", "reason": "Not a recognised GitHub URL.", "repos": []}
    u, repo = p
    try:
        if repo: names = [repo]
        else:
            s, lst = _get(f"/users/{u}/repos?sort=updated&per_page=5")
            if s != 200: return {**base, "status": "unavailable", "reason": f"GitHub API returned {s} for the profile.", "repos": []}
            names = [r["name"] for r in lst[:5]]
        repos = [_repo(u, n) for n in names]
        return {**base, "status": "checked", "reason": None, "repos": repos}
    except _Limited: return {**base, "status": "rate_limited", "reason": "GitHub API rate limit reached; set GITHUB_TOKEN or retry later.", "repos": []}
    except Exception as e: return {**base, "status": "unavailable", "reason": f"Network/API error ({type(e).__name__}).", "repos": []}
