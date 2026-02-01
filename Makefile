.PHONY: install dev run test lint format migrate seed docker-build docker-up docker-down clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	pre-commit install

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v

test-cov:
	pytest -v --cov=app --cov-report=term-missing

lint:
	ruff check .
	black --check .

format:
	ruff check --fix .
	black .

migrate:
	alembic upgrade head

migrate-create:
	@read -p "Migration message: " msg; alembic revision --autogenerate -m "$$msg"

seed:
	python -m scripts.seed_db

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov .ruff_cache
