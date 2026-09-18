#!/usr/bin/env bash
# One-shot: install (first time) and run backend + frontend.
set -e
cd "$(dirname "$0")"
if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -r backend/requirements.txt
fi
[ -f backend/.env ] || cp backend/.env.example backend/.env
[ -f frontend/.env ] || cp frontend/.env.example frontend/.env
[ -d frontend/node_modules ] || (cd frontend && npm install)
if grep -q paste_your_finnhub_key_here backend/.env; then
  echo "!! Put your Finnhub key in backend/.env (FINNHUB_API_KEY=...) — get one free at https://finnhub.io/register"; exit 1
fi
trap 'kill 0' INT
(cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm run dev) &
wait
