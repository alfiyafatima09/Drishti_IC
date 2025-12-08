.PHONY: install run format lint type-check test clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make run          - Run the API server and model (with GPU auto-detection)"
	@echo "  make format       - Format code using Ruff"
	@echo "  make lint         - Lint code using Ruff"
	@echo "  make type-check   - Run static type checking using Mypy"
	@echo "  make test         - Run tests using Pytest"
	@echo "  make clean        - Clean up cache files"
	@echo ""
	@echo "GPU Configuration:"
	@echo "  The script auto-detects GPU and CUDA. To force CPU mode:"
	@echo "    LLAMA_GPU_LAYERS=0 make run"
	@echo "  To force specific GPU layers:"
	@echo "    LLAMA_GPU_LAYERS=32 make run"

# Install dependencies
install:
	./venv/bin/pip install -r requirements.txt

# Run the API server and Model server
run:
	./start_services.sh

# Format code using Ruff
format:
	./venv/bin/ruff format app

# Lint code and fix issues using Ruff
lint:
	./venv/bin/ruff check --fix app

# Run static type checking using Mypy
type-check:
	./venv/bin/mypy app

# Run tests using Pytest (invoke via python -m to add CWD to path)
test:
	./venv/bin/python -m pytest

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
