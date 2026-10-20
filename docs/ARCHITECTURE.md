# Architecture
React/Vite SPA -> FastAPI (/api/v1) -> SQLAlchemy (SQLite dev / PostgreSQL prod) + private file storage.
Background work: `Job` table + in-process thread pool (`app/jobs.py`); abandoned jobs are re-queued on startup; max 2 attempts; document indexing is idempotent.
Modules: `extract` (PDF/DOCX/TXT validation + extraction) -> `rag` (chunking, embeddings, BM25, RRF) -> `qa` (answer + citation validation) ; `docintel` (summary, compare, research);
`evidence` (shared evidence engine used by Q&A and CV analysis); `cv` + `cv_pipeline` + `github` (recruitment).

## Retrieval
Hybrid: BM25 + embedding cosine, fused with Reciprocal Rank Fusion (k=60), duplicate removal, character budget, no reranker.
Default embedder is a hashing embedder (no downloads; lexical similarity, NOT semantic). Set EMBED_PROVIDER=sbert for real semantic embeddings.
Vectors are stored as JSON and compared in Python (fine for small corpora; pgvector is NOT used in this build).

## Scoring formula (CV analysis)
value: supported_by_work_sample 1.0, listed_in_cv 0.8, partial 0.5, not_found / unable_to_verify = missing (no value).
overall = 100 * sum(weight*value) / sum(weight over ALL criteria); coverage = sum(weight with a value) / sum(weight).
Name, photo, gender, religion, ethnicity, age are never inputs. Results are decision support requiring human review.

## Security
Argon2 not used: passwords use stdlib scrypt. HTTP-only session cookie + CSRF header, login/register/forgot throttling (in-memory, single process),
server-side workspace checks on every resource (404 for foreign IDs), content-sniffed uploads, server-generated filenames, security headers, audit log.
Admins can only be created with `python scripts/make_admin.py email`.
