.PHONY: dev dev-backend dev-frontend install install-backend install-frontend migrate test lint docker-up docker-down

# --- Development ---
dev:
	@echo "Starting all services..."
	docker compose -f docker-compose.dev.yml up -d postgres redis minio
	@$(MAKE) dev-backend &
	@$(MAKE) dev-frontend &
	@$(MAKE) dev-worker

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev-worker:
	cd backend && uv run celery -A app.workers.celery_app worker -l info -Q default,sync,ai

dev-beat:
	cd backend && uv run celery -A app.workers.celery_app beat -l info

# --- Install ---
install: install-backend install-frontend

install-backend:
	cd backend && uv sync

install-frontend:
	cd frontend && npm install

# --- Database ---
migrate:
	cd backend && uv run alembic upgrade head

migrate-new:
	cd backend && uv run alembic revision --autogenerate -m "$(msg)"

migrate-down:
	cd backend && uv run alembic downgrade -1

# --- Testing ---
test:
	cd backend && uv run pytest -v

test-cov:
	cd backend && uv run pytest --cov=app --cov-report=html

# --- Linting ---
lint:
	cd backend && uv run ruff check app/ && uv run ruff format --check app/

format:
	cd backend && uv run ruff check --fix app/ && uv run ruff format app/

# --- Docker ---
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-build:
	docker compose build
