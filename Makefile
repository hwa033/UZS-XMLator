.PHONY: build up down logs run-local test-health

build:
	docker build -t xml-automation:latest .

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f web

run-local:
	# activate venv then run (Windows PowerShell example)
	@echo "Run locally: activate your venv then: python -m flask run --host=127.0.0.1 --port=5000"

test-health:
	@curl -fsS http://127.0.0.1:5000/health || (echo "health check failed"; exit 1)
