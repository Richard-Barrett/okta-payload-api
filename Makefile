.PHONY: install dev test lint docker-up docker-down

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -e '.[dev]'

dev:
	. .venv/bin/activate && uvicorn app.main:app --reload --port 8000

test:
	. .venv/bin/activate && pytest -q

lint:
	. .venv/bin/activate && ruff check .

docker-up:
	docker compose up --build

docker-down:
	docker compose down
