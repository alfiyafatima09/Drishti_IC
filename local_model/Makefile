.PHONY: install run format lint clean

# Install dependencies
install:
	./venv/bin/pip install -r requirements.txt

# Run the API server with auto-reload
run:
	./start_server.sh

# Format code using Ruff
format:
	./venv/bin/ruff format app

# Lint code and fix issues using Ruff
lint:
	./venv/bin/ruff check --fix app

# Run static type checking using Mypy
type-check:
	./venv/bin/mypy app

# Run tests using Pytest
test:
	./venv/bin/pytest

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
