import re
from collections import Counter
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Chunk, Document
from .rag import tokens, STOP

SENT = re.compile(r"(?<=[.!?])\s+")
def sentences(db: Session, doc_id: int, cap=800):
    out = []
    for c in db.scalars(select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.idx)):
        for s in SENT.split(c.text):
            if len(s.split()) >= 5: out.append({"text": s.strip(), "page": c.page, "chunk_id": c.id, "heading": c.heading})
            if len(out) >= cap: return out
    return out

def summarize(db: Session, doc: Document):
    sents = sentences(db, doc.id)
    tf = Counter(w for s in sents for w in tokens(s["text"]))
    for s in sents: s["score"] = sum(tf[w] for w in tokens(s["text"])) / (len(s["text"].split()) ** 0.8)
    top = sorted(sents, key=lambda s: -s["score"])[:6]; top.sort(key=lambda s: (s["chunk_id"]))
    text = " ".join(s["text"] for s in sents)
    ents = Counter(m for m in re.findall(r"\b(?:[A-Z][a-z]+(?:\s[A-Z][a-z]+)+)\b", text))
    lim = [s for s in sents if re.search(r"\blimitation|limited by|future work|not able to|cannot\b", s["text"], re.I)][:5]
    return {"mode": "extractive", "note": "Sentences are copied from the document (extractive summary), not generated or paraphrased.",
            "overview": top[:2], "key_findings": top, "key_terms": [w for w, _ in tf.most_common(10)],
            "entities": [e for e, _ in ents.most_common(10)], "dates": sorted(set(re.findall(r"\b(?:19|20)\d{2}\b", text)))[:15],
            "stated_limitations": lim}

def _nums(s): return set(re.findall(r"\d+(?:\.\d+)?%?", s))
def _neg(s): return bool(re.search(r"\b(not|no|never|without|cannot|n't)\b", s, re.I))

def compare(db: Session, docs: list[Document]):
    data = {}
    for d in docs:
        ss = sentences(db, d.id, 400); data[d.id] = ss
    tops = {d.id: [w for w, _ in Counter(w for s in data[d.id] for w in tokens(s["text"])).most_common(30)] for d in docs}
    common = set.intersection(*[set(v) for v in tops.values()]) if tops else set()
    title = {d.id: d.title for d in docs}; conflicts = []
    ids = list(data)
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            for sa in data[ids[a]]:
                ta = set(tokens(sa["text"]))
                if len(ta) < 4: continue
                for sb in data[ids[b]]:
                    tb = set(tokens(sb["text"]))
                    if len(ta & tb) / len(ta | tb) < 0.45: continue
                    na, nb = _nums(sa["text"]), _nums(sb["text"])
                    reasons = []
                    if na and nb and na != nb: reasons.append("different numbers")
                    if _neg(sa["text"]) != _neg(sb["text"]): reasons.append("one statement is negated")
                    if reasons:
                        conflicts.append({"statement_a": {**sa, "document_id": ids[a], "document": title[ids[a]]},
                                          "statement_b": {**sb, "document_id": ids[b], "document": title[ids[b]]},
                                          "why_flagged": ", ".join(reasons),
                                          "caution": "Differences in dates, populations, definitions or context may explain this; it is not proof of contradiction.",
                                          "review_status": "needs_human_review"})
    return {"method": "deterministic lexical-overlap heuristic (no LLM)", "common_terms": sorted(common),
            "distinct_terms": {title[i]: [w for w in tops[i] if w not in common][:10] for i in tops},
            "possible_conflicts": conflicts[:20]}

SECTIONS = {"research_problem": ["introduction", "problem", "background"], "objectives": ["objective", "aim", "contribution"],
            "methodology": ["method", "approach", "model", "architecture"], "datasets": ["dataset", "data", "corpus"],
            "results": ["result", "experiment", "evaluation", "finding"], "limitations": ["limitation"], "future_work": ["future"], "conclusion": ["conclusion"]}
METRIC = re.compile(r"\b(accuracy|precision|recall|f1(?:[- ]score)?|auc|bleu|rouge|rmse|mae|map)\b[^.\n]{0,40}?(\d+(?:\.\d+)?\s?%?)", re.I)

def research(db: Session, doc: Document):
    chunks = list(db.scalars(select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.idx)))
    out = {k: [] for k in SECTIONS}
    for c in chunks:
        h = (c.heading or "").lower()
        for k, keys in SECTIONS.items():
            if any(x in h for x in keys) and len(out[k]) < 3: out[k].append({"excerpt": c.text[:500], "page": c.page, "chunk_id": c.id, "heading": c.heading})
    sents = sentences(db, doc.id)
    metrics = [{"metric": m.group(1), "value": m.group(2), "page": s["page"], "chunk_id": s["chunk_id"]} for s in sents for m in METRIC.finditer(s["text"])][:15]
    lim = [s for s in sents if re.search(r"\blimitation|future work|future research\b", s["text"], re.I)][:6]
    return {"method": "heading- and pattern-based extraction", "sections": out, "metrics": metrics, "stated_limitations": lim,
            "not_found": [k for k, v in out.items() if not v],
            "note": "Sections not found are not necessarily absent; the paper may use different headings. References are not extracted."}

def research_gaps(db: Session, docs: list[Document]):
    per = {d.title: research(db, d)["stated_limitations"] for d in docs}
    return {"1_limitations_stated_by_authors": per,
            "2_differences_across_papers": compare(db, docs)["possible_conflicts"] if len(docs) > 1 else [],
            "3_ai_hypotheses": [],
            "note": "AI-generated hypotheses require a configured LLM provider and are not produced in extractive mode. "
                    "A small collection of papers cannot establish that a gap is novel; a wider literature review is recommended."}
