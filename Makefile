.PHONY: setup backend frontend dev docker

setup:            ## install everything and create .env files
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	test -f backend/.env || cp backend/.env.example backend/.env
	cd frontend && npm install
	test -f frontend/.env || cp frontend/.env.example frontend/.env
	@echo "→ Now put your Finnhub key in backend/.env, then: make dev"

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:              ## run both (Ctrl-C stops both)
	@trap 'kill 0' INT; $(MAKE) backend & $(MAKE) frontend & wait

docker:
	docker compose up --build
