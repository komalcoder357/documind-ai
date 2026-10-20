"""CV parsing, transparent scoring and interview questions. Deterministic and LLM-free."""
import re
from datetime import datetime
from .evidence import verify_excerpt

SECTION_NAMES = {"skills": r"(technical\s+)?skills|technologies|core competencies", "education": r"education|academic.*",
                 "experience": r"(work\s+|professional\s+)?experience|employment( history)?", "projects": r"(academic\s+|personal\s+)?projects?",
                 "certifications": r"certifications?|certificates?", "publications": r"publications?", "achievements": r"achievements?|awards?"}
LEVELS = {"diploma": 1, "bachelor": 2, "master": 3, "phd": 4}
LEVEL_RE = [("phd", r"\bph\.?d\b|doctorate"), ("master", r"\bmaster'?s?\b|\bm\.?sc\b|\bmba\b|\bms\s*(?:in|cs)\b|\bm\.?s\.?\b(?=\s+(?:in|of))"),
            ("bachelor", r"\bbachelor'?s?\b|\bb\.?sc\b|\bbs(?:cs)?\b|\bb\.?e\b|\bb\.?tech\b|\bbba\b"), ("diploma", r"\bdiploma\b|\bassociate degree\b")]
VALUE = {"supported_by_work_sample": 1.0, "listed_in_cv": 0.8, "partial": 0.5, "not_found": None, "unable_to_verify": None}
FORMULA = ("overall = 100 * sum(weight_i * value_i) / sum(weight_i over ALL criteria); value = 1.0 supported_by_work_sample, 0.8 listed_in_cv, 0.5 partial; "
           "not_found / unable_to_verify have NO value (shown as missing, and they lower the overall score only because the evidence is absent). "
           "coverage = sum(weight_i with a value) / sum(weight_i). Name, photo, gender, religion, ethnicity, age and similar traits are never used.")

def term_re(t): return re.compile(r"(?<![A-Za-z0-9+#])" + re.escape(t.strip()) + r"(?![A-Za-z0-9+#])", re.I)
def snippet(text, m, pad=70): return re.sub(r"\s+", " ", text[max(0, m.start() - pad): m.end() + pad]).strip()

def split_sections(text):
    secs, cur = {}, None
    for line in text.splitlines():
        s = line.strip().rstrip(":").strip()
        hit = next((k for k, p in SECTION_NAMES.items() if len(s) < 40 and re.fullmatch(p, s, re.I)), None)
        if hit: cur = hit; secs.setdefault(cur, []); continue
        if cur and line.strip(): secs[cur].append(line.strip())
    return secs

def years_experience(text, secs):
    for line in text.splitlines():
        if re.search(r"experience", line, re.I):
            m = re.findall(r"(\d{1,2})\+?\s*(?:years?|yrs)", line, re.I)
            if m: return max(int(x) for x in m), line.strip()[:160]
    if "experience" in secs:
        iv = []
        for a, b in re.findall(r"((?:19|20)\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2}|present|current)", " ".join(secs["experience"]), re.I):
            iv.append((int(a), datetime.now().year if b.lower() in ("present", "current") else int(b)))
        iv.sort(); tot, end = 0, 0
        for a, b in iv:
            a = max(a, end); tot += max(0, b - a); end = max(end, b)
        if tot: return tot, "date ranges in the experience section"
    return None, None

def highest_level(text):
    best = None
    for lvl, pat in LEVEL_RE:
        m = re.search(pat, text, re.I)
        if m and (best is None or LEVELS[lvl] > LEVELS[best[0]]): best = (lvl, snippet(text, m))
    return best

def parse_cv(text: str):
    secs = split_sections(text); warnings = []
    urls = [u.rstrip(".,;") for u in re.findall(r"(?:https?://|www\.)[^\s)>\]]+|(?:github\.com|linkedin\.com/in)/[^\s)>\]]+", text)]
    links = {"github": [], "linkedin": [], "other": []}
    for u in dict.fromkeys(urls):
        full = u if u.startswith("http") else "https://" + u
        (links["github"] if "github.com" in full.lower() else links["linkedin"] if "linkedin.com" in full.lower() else links["other"]).append(full)
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text); phone = re.search(r"\+?\d[\d\s().-]{8,}\d", text)
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    name = first if 1 < len(first.split()) <= 4 and not re.search(r"[\d@]", first) else None
    y, ysrc = years_experience(text, secs); lvl = highest_level(" ".join(secs.get("education", [])) or text)
    if not secs: warnings.append("No standard section headings (Skills, Education, Experience...) were detected; extraction may be incomplete.")
    if not email: warnings.append("No email address found.")
    return {"name": name, "name_note": "Display only; never used in scoring.", "email": email.group(0) if email else None, "phone": phone.group(0).strip() if phone else None,
            "links": links, "skills_section": secs.get("skills", [])[:30], "education": secs.get("education", [])[:10], "experience": secs.get("experience", [])[:30],
            "projects": secs.get("projects", [])[:12], "certifications": secs.get("certifications", [])[:10], "publications": secs.get("publications", [])[:10],
            "achievements": secs.get("achievements", [])[:10], "years_experience": y, "years_source": ysrc,
            "education_level": lvl[0] if lvl else None, "education_source": lvl[1] if lvl else None, "extraction_warnings": warnings}

def build_criteria(required=(), preferred=(), min_years=None, education=None, weights=None):
    out = []
    for lvl, items, w in (("required", required, 3), ("preferred", preferred, 1)):
        for s in items:
            s = s.strip()
            if s: out.append({"type": "skill", "level": lvl, "target": s, "aliases": [], "weight": w})
    if min_years: out.append({"type": "experience", "level": "required", "target": int(min_years), "weight": 2})
    if education and education.lower() in LEVELS: out.append({"type": "education", "level": "required", "target": education.lower(), "weight": 1})
    for i, c in enumerate(out): c["id"] = i + 1; c["name"] = c["target"] if c["type"] == "skill" else f"{c['type'].title()}: {c['target']}"
    return out

def _skill(c, text, portfolio):
    terms = [c["target"]] + c.get("aliases", []); ev, in_cv, in_repo = [], False, False
    for t in terms:
        m = term_re(t).search(text)
        if m:
            ex = snippet(text, m); in_cv = True
            ev.append({"source_type": "cv", "location": "CV text", "excerpt": ex, "verification": verify_excerpt(ex, text)}); break
    for link in portfolio:
        for r in link.get("repos", []):
            if r.get("status") != "checked": continue
            for t in terms:
                rx = term_re(t); lang = next((f"{k} {v}%" for k, v in r["languages"].items() if k.lower() == t.lower()), None)
                src = lang or (f"topic: {t}" if any(x.lower() == t.lower() for x in r["topics"]) else None)
                m = rx.search(r.get("readme_text", "")) if not src else None
                if src or m:
                    ex = src or snippet(r["readme_text"], m)
                    ev.append({"source_type": "repository", "location": f"{r['name']} ({link['url']})", "excerpt": ex,
                               "verification": verify_excerpt(ex, r.get("readme_text", "")) if m else "supported",
                               "caveat": "Fork" if r.get("fork") else "Authorship/contribution not established"}); in_repo = True; break
            if in_repo: break
        if in_repo: break
    if in_repo: return "supported_by_work_sample", "Mentioned in the CV and visible in a public repository (authorship not established)." if in_cv else "Visible in a public repository; not stated in the CV text (authorship not established).", ev
    if in_cv: return "listed_in_cv", "Listed in the CV; not backed by a reviewed work sample.", ev
    return "not_found", "Not found in the CV text. Absence of evidence is not evidence of absence; clarify at interview.", ev

def assess(profile, text, criteria, portfolio):
    res = []
    for c in criteria:
        st, why, ev = "unable_to_verify", "", []
        if c["type"] in ("skill", "keyword"): st, why, ev = _skill(c, text, portfolio)
        elif c["type"] == "experience":
            y = profile.get("years_experience")
            if y is None: st, why = "unable_to_verify", "Years of experience could not be determined from the CV."
            else:
                st = "listed_in_cv" if y >= int(c["target"]) else "partial"; why = f"CV indicates about {y} year(s); requirement is {c['target']}."
                ev = [{"source_type": "cv", "location": "CV text", "excerpt": profile.get("years_source") or "", "verification": "supported"}]
        elif c["type"] == "education":
            lv = profile.get("education_level")
            if not lv: st, why = "not_found", "No degree level detected in the CV."
            else:
                st = "listed_in_cv" if LEVELS[lv] >= LEVELS[c["target"]] else "partial"; why = f"Highest detected level: {lv}; required: {c['target']}."
                ev = [{"source_type": "cv", "location": "CV text", "excerpt": profile.get("education_source") or "", "verification": verify_excerpt(profile.get("education_source") or "", text)}]
        res.append({**c, "status": st, "value": VALUE[st], "explanation": why, "evidence": ev})
    tw = sum(c["weight"] for c in criteria)
    if not tw: return res, None, None
    got = sum(r["weight"] * r["value"] for r in res if r["value"] is not None)
    cov = sum(r["weight"] for r in res if r["value"] is not None)
    return res, round(100 * got / tw, 1), round(100 * cov / tw, 1)

def interview_questions(profile, results):
    qs = []
    for r in results:
        t = r["target"]; ref = r["evidence"][0]["location"] if r["evidence"] else None
        if r["type"] == "skill" and r["status"] in ("listed_in_cv", "supported_by_work_sample"):
            qs.append({"question": f"Describe a concrete problem you solved with {t}. What was your specific role and what trade-offs did you make?", "skill": t,
                       "why": "Skill is claimed in the CV" + (" and visible in a public repository" if r["status"] == "supported_by_work_sample" else "") + "; confirm depth and personal contribution.",
                       "evidence_ref": ref, "rubric": ["Specific example with context", "Clear personal contribution", "Understands limitations and alternatives"]})
        elif r["type"] == "skill":
            qs.append({"question": f"Your CV does not mention {t}. Do you have any experience with it, or with similar tools?", "skill": t,
                       "why": "No evidence found; this is a clarification, not an assumption that the skill is absent.", "evidence_ref": None,
                       "rubric": ["Honest description of exposure", "Ability to relate related experience", "Learning plan if applicable"]})
        elif r["type"] == "experience":
            qs.append({"question": "Walk me through your most relevant roles and the responsibilities you held in each.", "skill": "Experience",
                       "why": r["explanation"], "evidence_ref": ref, "rubric": ["Consistent timeline", "Increasing responsibility", "Relevance to the role"]})
    for p in profile.get("projects", [])[:3]:
        qs.append({"question": f"Tell me about your project: \"{p[:100]}\". What would you do differently now?", "skill": "Project experience",
                   "why": "Project listed in the CV.", "evidence_ref": "CV projects section", "rubric": ["Technical decisions explained", "Own contribution clear", "Reflects on lessons learned"]})
    return qs
