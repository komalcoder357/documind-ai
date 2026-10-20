#!/usr/bin/env bash
# Starts DocuMind AI (backend + frontend) together. Ctrl+C stops both. Needs Python 3.10+ and Node 18+.
set -e
cd "$(dirname "$0")"
[ -d backend/.venv ] || python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -q -r backend/requirements-dev.txt
(cd backend && alembic upgrade head)
[ -d frontend/node_modules ] || (cd frontend && npm install)
(cd backend && uvicorn app.main:app --reload) &
BACK=$!
trap 'kill $BACK 2>/dev/null' EXIT INT TERM
echo "Open http://localhost:5173  (API docs: http://127.0.0.1:8000/docs)"
cd frontend && npm run dev
