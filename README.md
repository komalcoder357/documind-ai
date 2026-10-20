# DocuMind AI

Document intelligence (upload, hybrid-retrieval Q&A with validated citations, summaries, comparison, research analysis) and evidence-based CV analysis (criteria, weights, GitHub checks, interview questions, reports), with the Doci mascot.

## Run everything with one command
    Windows: double-click run.bat      Mac/Linux: ./run.sh      then open http://localhost:5173

## Run locally (manual, two terminals)
    # backend
    cd backend && python -m venv .venv && source .venv/bin/activate
    pip install -r requirements-dev.txt
    alembic upgrade head                      # creates the database schema
    uvicorn app.main:app --reload             # API docs: http://127.0.0.1:8000/docs
    # frontend (new terminal)
    cd frontend && npm install && npm run dev # http://localhost:5173 (proxies /api to :8000)
    # make an admin (optional)
    cd backend && python scripts/make_admin.py you@example.com

## Tests
    cd backend && python -m pytest -q         # 39 backend tests
    cd frontend && npm test && npm run build  # 3 frontend tests + type-checked build

## Docker (not executed in the build environment)
    cp .env.example .env   # set POSTGRES_PASSWORD, then:  docker compose up --build   -> http://localhost:8080

## Honest status / known limitations
- Without an LLM key, Q&A runs in **extractive mode** (shows retrieved passages, labelled as such). Set LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY for written answers (code path is mocked in tests, not tested against the live API).
- Default embeddings are lexical hashing, not semantic. pgvector, Celery/Redis and cross-encoder reranking are **not implemented**; jobs run in an in-process thread pool (single server).
- OCR is not implemented: scanned PDFs are reported as needing OCR. DOCX/TXT have no pages, so citations show no page number.
- Email is not sent: password-reset tokens are only returned in dev mode (DEV_RETURN_RESET_TOKEN=true). Email verification is not implemented.
- GitHub inspection uses the official API (mocked in tests; live API not exercised). LinkedIn/other links are listed as "not checked" and never scraped.
- Contradiction detection is a lexical heuristic that flags pairs for human review. AI research-gap hypotheses require an LLM and are empty otherwise.
- Not implemented: notification center, Playwright browser E2E tests (an API-level end-to-end flow was run manually), malware scanning, dedicated admin config UI for providers.
- Docker files and PostgreSQL were not run here; only SQLite was exercised. Review security settings (HTTPS, COOKIE_SECURE, CORS) before any deployment. Not production-ready until you test it in your environment.
