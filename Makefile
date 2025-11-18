# Drishti IC Verification System - Makefile
# Complete development workflow automation

.PHONY: help install dev backend frontend down clean fmt lint logs db-migrate db-reset docker-build docker-up docker-down contracts-lint contracts-gen

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ General

help: ## Display this help message
	@echo "$(BLUE)Drishti IC Verification System$(NC)"
	@echo "================================"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(YELLOW)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(GREEN)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

install: setup-venv check-node ## Install all dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	@if [ ! -d "frontend/node_modules" ]; then \
		cd frontend && npm install; \
	else \
		echo "$(YELLOW)Frontend dependencies already installed. Run 'make clean-frontend' to reinstall$(NC)"; \
	fi
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

check-node: ## Check Node.js and npm installation
	@echo "$(BLUE)Checking Node.js and npm...$(NC)"
	@command -v node >/dev/null 2>&1 || { \
		echo "$(RED)✗ Node.js not found!$(NC)"; \
		echo "$(YELLOW)Install Node.js:$(NC)"; \
		echo "  macOS: $(BLUE)brew install node$(NC)"; \
		echo "  Or visit: $(BLUE)https://nodejs.org/$(NC)"; \
		exit 1; \
	}
	@command -v npm >/dev/null 2>&1 || { \
		echo "$(RED)✗ npm not found!$(NC)"; \
		exit 1; \
	}
	@echo "$(GREEN)✓ Node $(shell node --version)$(NC)"
	@echo "$(GREEN)✓ npm $(shell npm --version)$(NC)"

##@ Development

# Detect Python command - prefer Python 3.11 for compatibility
PYTHON311 := $(shell command -v python3.11 2> /dev/null)
PYTHON := $(shell command -v python3 2> /dev/null || command -v python 2> /dev/null)
VENV_DIR := venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip

check-python: ## Check Python version and availability
	@echo "$(BLUE)Checking Python installation...$(NC)"
	@if [ -n "$(PYTHON311)" ]; then \
		echo "$(GREEN)✓ Python 3.11 found: $(PYTHON311)$(NC)"; \
		$(PYTHON311) --version; \
	elif [ -n "$(PYTHON)" ]; then \
		echo "$(YELLOW)⚠️  Python 3.11 not found$(NC)"; \
		echo "Current Python: $(PYTHON)"; \
		$(PYTHON) --version; \
		echo "$(YELLOW)For best compatibility, install Python 3.11:$(NC)"; \
		echo "  brew install python@3.11"; \
	else \
		echo "$(RED)✗ No Python found!$(NC)"; \
		echo "$(YELLOW)Install Python 3.11:$(NC)"; \
		echo "  brew install python@3.11"; \
		exit 1; \
	fi

dev: ## Start both backend and frontend in parallel
	@echo "$(GREEN)Starting development environment...$(NC)"
	@$(MAKE) -j2 backend frontend

backend: setup-venv ## Start backend server (FastAPI)
	@echo "$(GREEN)Starting backend server...$(NC)"
	@echo "$(BLUE)Killing existing process on port 8000...$(NC)"
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	@sleep 1
	@mkdir -p logs
	@if [ -d "$(VENV_DIR)" ]; then \
		cd backend && ../$(VENV_PYTHON) main.py; \
	else \
		cd backend && $(PYTHON) main.py; \
	fi

frontend: check-node ## Start frontend dev server (Next.js)
	@echo "$(GREEN)Starting frontend server...$(NC)"
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "$(YELLOW)⚠️  Frontend dependencies not installed$(NC)"; \
		echo "$(BLUE)Installing dependencies first...$(NC)"; \
		cd frontend && npm install; \
	fi
	@echo "$(BLUE)Killing existing processes on ports 3000-3003...$(NC)"
	@for port in 3000 3001 3002 3003; do \
		lsof -ti:$$port | xargs kill -9 2>/dev/null || true; \
	done
	@sleep 1
	@echo "$(BLUE)Using default config: API at http://localhost:8000$(NC)"
	@$(MAKE) show-network-urls &
	cd frontend && npm run dev

frontend-ngrok: ## Start frontend with ngrok tunnel (for public access)
	@echo "$(GREEN)Starting frontend with ngrok tunnel...$(NC)"
	@echo "$(YELLOW)⚠️  Important: Backend will run on localhost:8000$(NC)"
	@echo "$(YELLOW)   Make sure your device can reach localhost or use network IP$(NC)"
	@echo ""
	@if ! command -v ngrok >/dev/null 2>&1; then \
		echo "$(RED)✗ ngrok not found!$(NC)"; \
		echo "$(YELLOW)Install ngrok:$(NC)"; \
		echo "  macOS: $(BLUE)brew install ngrok/ngrok/ngrok$(NC)"; \
		echo "  Or download: $(BLUE)https://ngrok.com/download$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Killing existing ngrok tunnels...$(NC)"
	@pkill -f ngrok || true
	@sleep 2
	@echo "$(BLUE)Killing existing processes on ports 3000-3003...$(NC)"
	@for port in 3000 3001 3002 3003; do \
		lsof -ti:$$port | xargs kill -9 2>/dev/null || true; \
	done
	@sleep 1
	@echo "$(BLUE)Starting frontend server first...$(NC)"
	@cd frontend && npm run dev > /tmp/nextjs.log 2>&1 &
	@sleep 8
	@FRONTEND_PORT=$$(lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -E ':(300[0-9]|3000)' | grep node | head -1 | awk '{print $$9}' | cut -d: -f2 | head -1); \
	if [ -z "$$FRONTEND_PORT" ]; then \
		FRONTEND_PORT=$$(netstat -an 2>/dev/null | grep LISTEN | grep -E '\.(300[0-9]|3000)' | head -1 | awk '{print $$4}' | cut -d: -f2 | cut -d. -f1); \
	fi; \
	if [ -z "$$FRONTEND_PORT" ]; then \
		FRONTEND_PORT="3000"; \
	fi; \
	echo "$(BLUE)Starting ngrok tunnel on port $$FRONTEND_PORT...$(NC)"; \
	ngrok http $$FRONTEND_PORT --log=stdout > /tmp/ngrok.log 2>&1 &
	@sleep 5
	@echo "$(BLUE)Fetching ngrok public URL...$(NC)"
	@for i in 1 2 3 4 5; do \
		NGROK_URL=$$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['tunnels'][0]['public_url'] if data.get('tunnels') else '')" 2>/dev/null); \
		if [ -z "$$NGROK_URL" ]; then \
			NGROK_URL=$$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -oE '"public_url":"https://[^"]*' | head -1 | sed 's/"public_url":"//' | sed 's/"//'); \
		fi; \
		if [ -n "$$NGROK_URL" ]; then \
			break; \
		fi; \
		sleep 1; \
	done; \
	if [ -n "$$NGROK_URL" ]; then \
		NGROK_URL_SKIP=$$(echo "$$NGROK_URL" | sed 's|$$|?ngrok-skip-browser-warning=1|'); \
		echo ""; \
		echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"; \
		echo "$(GREEN)  ✅ Ngrok Tunnel Active$(NC)"; \
		echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"; \
		echo "$(BLUE)🌍 Frontend URL (Use on your phone):$(NC)"; \
		echo "  $(GREEN)$$NGROK_URL_SKIP$(NC)"; \
		echo ""; \
		echo "$(BLUE)🔧 Backend URL (for WebSocket):$(NC)"; \
		echo "  $(GREEN)http://localhost:8000$(NC)  $(YELLOW)# Backend NOT on ngrok$(NC)"; \
		echo ""; \
		echo "$(YELLOW)⚠️  Important Notes:$(NC)"; \
		echo "  • Frontend is on ngrok (HTTPS)"; \
		echo "  • Backend is on localhost:8000 (HTTP)"; \
		echo "  • $(RED)Your phone cannot reach localhost from ngrok!$(NC)"; \
		echo "  • $(GREEN)Solution: Test on same device or use network IP for backend$(NC)"; \
		echo ""; \
		echo "$(YELLOW)💡 Better option for mobile: Use network IP instead$(NC)"; \
		echo "  Run: $(BLUE)make frontend$(NC) and access via your local IP"; \
		echo "  Ngrok dashboard: $(BLUE)http://localhost:4040$(NC)"; \
		echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"; \
		echo ""; \
	else \
		echo "$(YELLOW)⚠️  Could not get ngrok URL automatically$(NC)"; \
		echo "$(BLUE)Check ngrok dashboard: http://localhost:4040$(NC)"; \
		echo "$(YELLOW)Or check logs: tail -f /tmp/ngrok.log$(NC)"; \
		echo "$(YELLOW)Frontend logs: tail -f /tmp/nextjs.log$(NC)"; \
	fi
	@echo "$(BLUE)Frontend running in background. Press Ctrl+C to stop.$(NC)"
	@wait

show-network-urls: ## Show network URLs for mobile access
	@sleep 3
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  📱 Network Access URLs for Mobile$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)💻 Localhost (for local testing):$(NC)"
	@echo "  Frontend: $(GREEN)http://localhost:3000$(NC)"
	@echo "  Backend:  $(GREEN)http://localhost:8000$(NC)"
	@echo ""
	@echo "$(BLUE)🌐 Network URLs (use these on your phone):$(NC)"
	@echo "  Frontend: $(GREEN)http://192.168.0.130:3000$(NC)  $(YELLOW)# Replace with your actual IP$(NC)"
	@echo "  Backend:  $(GREEN)http://192.168.0.130:8000$(NC)  $(YELLOW)# Replace with your actual IP$(NC)"
	@echo ""
	@echo "$(YELLOW)💡 Tips:$(NC)"
	@echo "  • Find your IP: Run $(GREEN)ifconfig$(NC) or $(GREEN)ipconfig$(NC) in terminal"
	@echo "  • Make sure phone and computer are on same WiFi"
	@echo "  • For HTTPS (camera works better): $(GREEN)make frontend-ngrok$(NC)"
	@echo "  • If CORS issues: Check browser extensions"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""

setup-venv: ## Setup virtual environment if it doesn't exist
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(BLUE)Creating virtual environment...$(NC)"; \
		if [ -n "$(PYTHON311)" ]; then \
			echo "$(GREEN)✓ Found Python 3.11, using it for best compatibility$(NC)"; \
			$(PYTHON311) -m venv $(VENV_DIR); \
		elif [ -n "$(PYTHON)" ]; then \
			PYTHON_VERSION=$$($(PYTHON) --version 2>&1 | grep -oE '[0-9]+\.[0-9]+'); \
			echo "$(YELLOW)⚠️  Python 3.11 not found. Using Python $$PYTHON_VERSION$(NC)"; \
			echo "$(YELLOW)⚠️  For best compatibility, install Python 3.11: brew install python@3.11$(NC)"; \
			$(PYTHON) -m venv $(VENV_DIR); \
		else \
			echo "$(RED)Error: Python not found!$(NC)"; \
			echo "$(YELLOW)Please install Python 3.11: brew install python@3.11$(NC)"; \
			exit 1; \
		fi; \
		echo "$(BLUE)Upgrading pip...$(NC)"; \
		. $(VENV_DIR)/bin/activate && pip install --upgrade pip setuptools wheel; \
		echo "$(BLUE)Installing backend dependencies (this may take a few minutes)...$(NC)"; \
		. $(VENV_DIR)/bin/activate && pip install -r models/requirements.txt || { \
			echo "$(YELLOW)Some packages failed to install. Installing core packages only...$(NC)"; \
			. $(VENV_DIR)/bin/activate && pip install fastapi uvicorn python-dotenv sqlalchemy alembic opencv-python Pillow pytesseract pdfplumber PyPDF2 numpy requests beautifulsoup4 pydantic pydantic-settings python-multipart psutil; \
			echo "$(YELLOW)Note: Some optional packages skipped due to compatibility issues$(NC)"; \
		}; \
		echo "$(GREEN)✓ Virtual environment created and dependencies installed$(NC)"; \
	fi

down: ## Stop all running services
	@echo "$(YELLOW)Stopping services...$(NC)"
	@pkill -f "uvicorn" || true
	@pkill -f "next dev" || true
	@echo "$(GREEN)✓ Services stopped$(NC)"

##@ Code Quality

fmt: fmt-backend fmt-frontend ## Format all code

fmt-backend: ## Format backend code (Python)
	@echo "$(BLUE)Formatting backend code...$(NC)"
	cd backend && ruff format .
	@echo "$(GREEN)✓ Backend formatted$(NC)"

fmt-frontend: ## Format frontend code (TypeScript/React)
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	cd frontend && npm run format
	@echo "$(GREEN)✓ Frontend formatted$(NC)"

lint: lint-backend lint-frontend ## Lint all code

lint-backend: ## Lint backend code
	@echo "$(BLUE)Linting backend...$(NC)"
	cd backend && ruff check .

lint-frontend: ## Lint frontend code
	@echo "$(BLUE)Linting frontend...$(NC)"
	cd frontend && npm run lint

##@ Database

db-migrate: setup-venv ## Run database migrations
	@echo "$(BLUE)Running migrations...$(NC)"
	@if [ -d "$(VENV_DIR)" ]; then \
		cd backend && ../$(VENV_PYTHON) -c "from models.database import init_database; init_database()"; \
	else \
		cd backend && $(PYTHON) -c "from models.database import init_database; init_database()"; \
	fi
	@echo "$(GREEN)✓ Migrations complete$(NC)"

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(RED)Resetting database...$(NC)"
	@rm -f data.sqlite
	@$(MAKE) db-migrate
	@echo "$(GREEN)✓ Database reset$(NC)"

db-shell: ## Open database shell
	@echo "$(BLUE)Opening database shell...$(NC)"
	sqlite3 data.sqlite

##@ Contracts (OpenAPI)

contracts-lint: ## Validate OpenAPI specification
	@echo "$(BLUE)Validating OpenAPI contract...$(NC)"
	@command -v openapi-generator-cli >/dev/null 2>&1 || { echo "$(YELLOW)Installing openapi-generator-cli...$(NC)"; npm install -g @openapitools/openapi-generator-cli; }
	openapi-generator-cli validate -i contracts/openapi.yaml
	@echo "$(GREEN)✓ Contract valid$(NC)"

contracts-gen: contracts-gen-frontend ## Generate types and models from OpenAPI

contracts-gen-frontend: ## Generate TypeScript types for frontend
	@echo "$(BLUE)Generating frontend types from OpenAPI...$(NC)"
	@command -v openapi-typescript >/dev/null 2>&1 || { echo "$(YELLOW)Installing openapi-typescript...$(NC)"; npm install -g openapi-typescript; }
	openapi-typescript contracts/openapi.yaml -o frontend/src/types/api.gen.ts
	@echo "$(GREEN)✓ Frontend types generated$(NC)"

##@ Docker

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build
	@echo "$(GREEN)✓ Images built$(NC)"

docker-up: ## Start services with Docker Compose
	@echo "$(GREEN)Starting Docker services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "$(BLUE)Backend: http://localhost:8000$(NC)"
	@echo "$(BLUE)Frontend: http://localhost:3000$(NC)"

docker-down: ## Stop Docker services
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-logs: ## View Docker logs
	docker-compose logs -f

##@ Utilities

logs: ## View application logs
	@echo "$(BLUE)Viewing logs (Ctrl+C to exit)...$(NC)"
	tail -f logs/*.log 2>/dev/null || echo "No logs found. Start services first."

clean: ## Clean temporary files and caches
	@echo "$(YELLOW)Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -prune -o -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	rm -rf logs/*.log 2>/dev/null || true
	@echo "$(GREEN)✓ Cleaned$(NC)"

clean-frontend: ## Clean frontend dependencies and build artifacts
	@echo "$(YELLOW)Cleaning frontend...$(NC)"
	rm -rf frontend/node_modules
	rm -rf frontend/.next
	rm -rf frontend/.turbo
	@echo "$(GREEN)✓ Frontend cleaned$(NC)"
	@echo "$(BLUE)Run 'make install' or 'make frontend' to reinstall$(NC)"

check-extensions: ## Check for problematic browser extensions causing CORS errors
	@echo "$(BLUE)Checking for browser extension issues...$(NC)"
	node scripts/check-extensions.js

setup-network-ip: ## Setup frontend to use network IP for mobile testing
	@echo "$(BLUE)Setting up network IP configuration...$(NC)"
	@bash scripts/setup-network-ip.sh

start-ngrok-full: ## Start both backend and frontend with ngrok (HTTPS everywhere)
	@bash scripts/start-with-ngrok.sh

clean-venv: ## Remove virtual environment (will be recreated on next run)
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	rm -rf $(VENV_DIR)
	@echo "$(GREEN)✓ Virtual environment removed$(NC)"
	@echo "$(BLUE)Run 'make backend' to recreate with Python 3.11$(NC)"

##@ Information

status: ## Show status of services
	@echo "$(BLUE)Service Status:$(NC)"
	@echo "Backend (port 8000):"
	@lsof -ti:8000 >/dev/null 2>&1 && echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"
	@echo "Frontend (port 3000):"
	@lsof -ti:3000 >/dev/null 2>&1 && echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"

ports: ## Show which ports are in use
	@echo "$(BLUE)Port Usage:$(NC)"
	@echo "Port 8000 (Backend):"
	@lsof -i:8000 || echo "  Not in use"
	@echo "\nPort 3000 (Frontend):"
	@lsof -i:3000 || echo "  Not in use"

##@ Quick Start

setup: check-node install db-migrate ## Complete initial setup
	@echo "$(GREEN)✓ Setup complete! Run 'make dev' to start development.$(NC)"

reinstall: clean-venv clean-frontend install ## Reinstall all dependencies from scratch
	@echo "$(GREEN)✓ All dependencies reinstalled$(NC)"

.DEFAULT_GOAL := help
