.PHONY: backend-install backend-migrate backend-seed backend-run backend-test frontend-install frontend-run frontend-build docker-up

backend-install:
	cd backend && pip install -r requirements.txt

backend-migrate:
	cd backend && alembic upgrade head

backend-seed:
	cd backend && python -m app.seed.seed_data

backend-run:
	cd backend && uvicorn app.main:app --reload --port 8000

backend-test:
	cd backend && pytest tests/ -v

frontend-install:
	cd frontend && npm install

frontend-run:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

docker-up:
	docker compose up --build

setup: backend-install backend-migrate backend-seed frontend-install
	@echo "Setup complete. Run 'make backend-run' and 'make frontend-run' in two terminals."
