import hashlib, math, re
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import config
from .models import Chunk

STOP = set("a an the and or of to in on for with by is are was were be been it this that these those as at from what which who how why when where do does did can could should would about into than then there their its not no".split())
TOKEN = re.compile(r"[a-z0-9+#]+")
def tokens(t: str, drop_stop=True): return [w for w in TOKEN.findall(t.lower()) if not (drop_stop and w in STOP)]

# ---- embeddings (configurable; default needs no download and is NOT semantic) ----
DIM = 384
def _hash_embed(text: str):
    v = [0.0] * DIM; tk = tokens(text)
    for g in tk + [a + "_" + b for a, b in zip(tk, tk[1:])]:
        h = int(hashlib.md5(g.encode()).hexdigest(), 16)
        v[h % DIM] += 1.0 if (h >> 100) & 1 else -1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [round(x / n, 5) for x in v]

_sbert = None
def embed(text: str):
    global _sbert
    if config.EMBED_PROVIDER == "sbert":
        if _sbert is None:
            from sentence_transformers import SentenceTransformer
            _sbert = SentenceTransformer(config.EMBED_MODEL)
        return [float(x) for x in _sbert.encode(text, normalize_embeddings=True)]
    return _hash_embed(text)

def embed_mode(): return "sentence-transformers (semantic)" if config.EMBED_PROVIDER == "sbert" else "hashing (lexical-similarity fallback, not semantic)"
def cosine(a, b): return sum(x * y for x, y in zip(a, b))

# ---- chunking ----
def is_heading(s: str):
    w = s.split()
    return (len(s) <= 80 and len(w) <= 8 and not s.endswith((".", ",", ";", ":")) and
            (s.isupper() or re.match(r"^\d+(\.\d+)*\.?\s+\S", s) or all(x[0].isupper() for x in w if x[0].isalpha())))

@dataclass
class Piece: page: int | None; heading: str | None; text: str

def chunk_pages(pages, size=None, overlap=None):
    size, overlap = size or config.CHUNK_WORDS, overlap if overlap is not None else config.CHUNK_OVERLAP
    out, heading = [], None
    for page, text in pages:
        segs, buf, seg_h = [], [], heading
        for line in text.splitlines():
            s = line.strip()
            if not s: continue
            if is_heading(s):
                if buf: segs.append((seg_h, " ".join(buf))); buf = []
                seg_h = heading = s[:200]
            else: buf.append(s)
        if buf: segs.append((seg_h, " ".join(buf)))
        for h, body in segs:
            words = body.split(); step = max(1, size - overlap)
            for i in range(0, len(words), step):
                piece = " ".join(words[i:i + size])
                if piece: out.append(Piece(page, h, piece))
                if i + size >= len(words): break
    return out

# ---- retrieval ----
def bm25(query, docs, k1=1.5, b=0.75):
    N = len(docs); avg = sum(len(d) for d in docs) / N if N else 0
    df = {t: sum(1 for d in docs if t in d) for t in set(query)}
    scores = []
    for d in docs:
        s = 0.0
        for t in set(query):
            f = d.count(t)
            if not f: continue
            idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(d) / (avg or 1)))
        scores.append(s)
    return scores

def rrf(rankings, k=60):
    sc = {}
    for r in rankings:
        for pos, key in enumerate(r): sc[key] = sc.get(key, 0) + 1 / (k + pos + 1)
    return sc

def retrieve(db: Session, ws: list[int], doc_ids: list[int], query: str, top_k=5, char_budget=6000):
    """Hybrid retrieval limited to authorized workspaces/documents. Returns (hits, pipeline)."""
    chunks = list(db.scalars(select(Chunk).where(Chunk.workspace_id.in_(ws), Chunk.document_id.in_(doc_ids)).order_by(Chunk.id)))
    pipeline = {"embedding": embed_mode(), "lexical": "BM25", "fusion": "Reciprocal Rank Fusion (k=60)", "reranker": "none", "top_k": top_k, "candidates": len(chunks)}
    q = tokens(query)
    if not chunks or not q: return [], pipeline
    bm = bm25(q, [tokens(c.text) for c in chunks])
    qv = embed(query); vs = [cosine(qv, c.embedding) for c in chunks]
    bm_rank = [i for i in sorted(range(len(chunks)), key=lambda i: -bm[i]) if bm[i] > 0]
    v_rank = [i for i in sorted(range(len(chunks)), key=lambda i: -vs[i]) if vs[i] >= config.MIN_VECTOR_SIM]
    fused = rrf([bm_rank, v_rank])
    hits, seen, used = [], set(), 0
    for i in sorted(fused, key=lambda i: -fused[i]):
        norm = " ".join(chunks[i].text.lower().split())
        if norm in seen: continue
        if used + len(chunks[i].text) > char_budget and hits: break
        seen.add(norm); used += len(chunks[i].text)
        hits.append({"chunk": chunks[i], "bm25": round(bm[i], 3), "vector": round(vs[i], 3), "fused": round(fused[i], 5)})
        if len(hits) >= top_k: break
    return hits, pipeline
