.PHONY: test test-unit test-integration test-contract test-e2e test-hard-cases run lint format clean

run:
	uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest tests/

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

test-contract:
	pytest tests/contract/

test-e2e:
	pytest tests/e2e/

test-hard-cases:
	pytest tests/hard_cases/

lint:
	ruff check .

format:
	ruff format .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
