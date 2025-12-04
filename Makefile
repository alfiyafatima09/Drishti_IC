# Drishti IC Verification System - Makefile
# Complete development workflow automation
# 
# Cross-platform support:
# - macOS: Native support
# - Windows: Works with Git Bash, WSL, or MSYS2
# - Linux: Native support
# 
# Platform-specific features:
# - Virtual environment paths (bin/ vs Scripts/)
# - Process management (lsof/pkill vs taskkill)
# - Temp directories (/tmp vs %TEMP%)
# - URL opening (open vs start vs xdg-open)
# - Python detection (python3 vs py)

.PHONY: help install dev backend frontend frontend-web frontend-build frontend-ngrok down clean fmt lint logs db-migrate db-reset docker-build docker-up docker-down contracts-lint contracts-gen check-go check-wails check-bun check-frontend-deps install-wails

# Virtual environment directory (must be defined before platform detection)
VENV_DIR := venv

# Platform detection
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    VENV_BIN := Scripts
    VENV_PYTHON := $(VENV_DIR)/$(VENV_BIN)/python.exe
    VENV_PIP := $(VENV_DIR)/$(VENV_BIN)/pip.exe
    VENV_ACTIVATE := $(VENV_DIR)/$(VENV_BIN)/activate
    PYTHON_CMD := py
    PYTHON3_CMD := py -3
    PYTHON311_CMD := py -3.11
    OPEN_CMD := start
    KILL_CMD := taskkill /F /IM
    PKILL_CMD := taskkill /F /FI
    SLEEP_CMD := timeout /t
    TEMP_DIR := $(TEMP)
    WHICH_CMD := where
    RM_CMD := del /Q /F
    RMDIR_CMD := rmdir /S /Q
    MKDIR_CMD := mkdir
    SHELL := cmd.exe
else
    DETECTED_OS := $(shell uname -s)
    VENV_BIN := bin
    VENV_PYTHON := $(VENV_DIR)/$(VENV_BIN)/python
    VENV_PIP := $(VENV_DIR)/$(VENV_BIN)/pip
    VENV_ACTIVATE := $(VENV_DIR)/$(VENV_BIN)/activate
    PYTHON_CMD := python3
    PYTHON3_CMD := python3
    PYTHON311_CMD := python3.11
    OPEN_CMD := open
    KILL_CMD := kill -9
    PKILL_CMD := pkill -f
    SLEEP_CMD := sleep
    TEMP_DIR := /tmp
    WHICH_CMD := command -v
    RM_CMD := rm -f
    RMDIR_CMD := rm -rf
    MKDIR_CMD := mkdir -p
endif

# Colors for output (Windows CMD doesn't support ANSI by default, but most modern terminals do)
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

install: setup-venv check-frontend-deps ## Install all dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	@echo "$(BLUE)Installing frontend dependencies (Bun)...$(NC)"
	@if [ ! -d "frontend/node_modules" ]; then \
		cd frontend && bun install; \
	else \
		echo "$(YELLOW)Frontend dependencies already installed. Run 'make clean-frontend' to reinstall$(NC)"; \
	fi
	@echo "$(BLUE)Syncing Go dependencies...$(NC)"
	@cd frontend && go mod tidy
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

check-node: ## Check Node.js and npm installation
	@echo "$(BLUE)Checking Node.js and npm...$(NC)"
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	command -v node >/dev/null 2>&1 || { \
		echo "$(RED)✗ Node.js not found!$(NC)"; \
		echo "$(YELLOW)Install Node.js:$(NC)"; \
		if [ "$$UNAME_S" = "Darwin" ]; then \
			echo "  macOS: $(BLUE)brew install node$(NC)"; \
		elif [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
			echo "  Windows: Download from $(BLUE)https://nodejs.org/$(NC)"; \
		else \
			echo "  Linux: Use your package manager or visit $(BLUE)https://nodejs.org/$(NC)"; \
		fi; \
		exit 1; \
	}
	@command -v npm >/dev/null 2>&1 || { \
		echo "$(RED)✗ npm not found!$(NC)"; \
		exit 1; \
	}
	@echo "$(GREEN)✓ Node $(shell node --version)$(NC)"
	@echo "$(GREEN)✓ npm $(shell npm --version)$(NC)"

check-go: ## Check Go installation
	@echo "$(BLUE)Checking Go installation...$(NC)"
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	command -v go >/dev/null 2>&1 || { \
		echo "$(RED)✗ Go not found!$(NC)"; \
		echo "$(YELLOW)Install Go 1.21+:$(NC)"; \
		if [ "$$UNAME_S" = "Darwin" ]; then \
			echo "  macOS: $(BLUE)brew install go$(NC)"; \
		elif [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
			echo "  Windows: Download from $(BLUE)https://go.dev/dl/$(NC)"; \
		else \
			echo "  Linux: $(BLUE)sudo apt install golang-go$(NC) or visit $(BLUE)https://go.dev/dl/$(NC)"; \
		fi; \
		exit 1; \
	}
	@echo "$(GREEN)✓ Go $$(go version | awk '{print $$3}')$(NC)"

check-wails: check-go ## Check Wails CLI installation
	@echo "$(BLUE)Checking Wails CLI...$(NC)"
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	command -v wails >/dev/null 2>&1 || { \
		echo "$(RED)✗ Wails CLI not found!$(NC)"; \
		echo "$(YELLOW)Install Wails CLI:$(NC)"; \
		echo "  $(BLUE)go install github.com/wailsapp/wails/v2/cmd/wails@latest$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Then add Go bin to PATH:$(NC)"; \
		if [ "$$UNAME_S" = "Darwin" ] || [ "$$UNAME_S" = "Linux" ]; then \
			echo "  $(BLUE)export PATH=\"\$$PATH:\$$(go env GOPATH)/bin\"$(NC)"; \
		else \
			echo "  Add $(BLUE)%GOPATH%\\bin$(NC) to your PATH environment variable"; \
		fi; \
		exit 1; \
	}
	@echo "$(GREEN)✓ Wails $$(wails version | head -1)$(NC)"

check-bun: ## Check Bun installation
	@echo "$(BLUE)Checking Bun installation...$(NC)"
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	command -v bun >/dev/null 2>&1 || { \
		echo "$(RED)✗ Bun not found!$(NC)"; \
		echo "$(YELLOW)Install Bun:$(NC)"; \
		if [ "$$UNAME_S" = "Darwin" ] || [ "$$UNAME_S" = "Linux" ]; then \
			echo "  $(BLUE)curl -fsSL https://bun.sh/install | bash$(NC)"; \
			echo "  or"; \
			echo "  macOS: $(BLUE)brew install oven-sh/bun/bun$(NC)"; \
		else \
			echo "  Windows: $(BLUE)powershell -c \"irm bun.sh/install.ps1 | iex\"$(NC)"; \
		fi; \
		exit 1; \
	}
	@echo "$(GREEN)✓ Bun $$(bun --version)$(NC)"

check-frontend-deps: check-go check-wails check-bun ## Check all frontend dependencies (Go, Wails, Bun)
	@echo "$(GREEN)✓ All frontend dependencies available$(NC)"

##@ Development

# Detect Python command - prefer Python 3.11 for compatibility
ifeq ($(OS),Windows_NT)
    PYTHON311 := $(shell where py >nul 2>&1 && py -3.11 --version >nul 2>&1 && echo py -3.11)
    PYTHON := $(shell where py >nul 2>&1 && py -3 --version >nul 2>&1 && echo py -3 || where python >nul 2>&1 && echo python)
else
    PYTHON311 := $(shell command -v python3.11 2> /dev/null)
    PYTHON := $(shell command -v python3 2> /dev/null || command -v python 2> /dev/null)
endif

check-python: ## Check Python version and availability
	@echo "$(BLUE)Checking Python installation...$(NC)"
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Windows"); \
	if [ "$$UNAME_S" = "Windows" ] || [ "$$OS" = "Windows_NT" ]; then \
		if py -3.11 --version >nul 2>&1; then \
			echo "$(GREEN)✓ Python 3.11 found$(NC)"; \
			py -3.11 --version; \
		elif py -3 --version >nul 2>&1; then \
			echo "$(YELLOW)⚠️  Python 3.11 not found$(NC)"; \
			py -3 --version; \
			echo "$(YELLOW)For best compatibility, install Python 3.11:$(NC)"; \
			echo "  Download from: https://www.python.org/downloads/"; \
		elif python --version >nul 2>&1; then \
			echo "$(YELLOW)⚠️  Python 3.11 not found$(NC)"; \
			python --version; \
			echo "$(YELLOW)For best compatibility, install Python 3.11:$(NC)"; \
			echo "  Download from: https://www.python.org/downloads/"; \
		else \
			echo "$(RED)✗ No Python found!$(NC)"; \
			echo "$(YELLOW)Install Python 3.11:$(NC)"; \
			echo "  Download from: https://www.python.org/downloads/"; \
			exit 1; \
		fi; \
	else \
		if [ -n "$(PYTHON311)" ]; then \
			echo "$(GREEN)✓ Python 3.11 found: $(PYTHON311)$(NC)"; \
			$(PYTHON311) --version; \
		elif [ -n "$(PYTHON)" ]; then \
			echo "$(YELLOW)⚠️  Python 3.11 not found$(NC)"; \
			echo "Current Python: $(PYTHON)"; \
			$(PYTHON) --version; \
			echo "$(YELLOW)For best compatibility, install Python 3.11:$(NC)"; \
			if [ "$$UNAME_S" = "Darwin" ]; then \
				echo "  macOS: $(BLUE)brew install python@3.11$(NC)"; \
			else \
				echo "  Linux: Use your package manager"; \
			fi; \
		else \
			echo "$(RED)✗ No Python found!$(NC)"; \
			echo "$(YELLOW)Install Python 3.11:$(NC)"; \
			if [ "$$UNAME_S" = "Darwin" ]; then \
				echo "  macOS: $(BLUE)brew install python@3.11$(NC)"; \
			else \
				echo "  Linux: Use your package manager"; \
			fi; \
			exit 1; \
		fi; \
	fi

dev: ## Start both backend and frontend (Wails desktop) in parallel
	@echo "$(GREEN)Starting development environment...$(NC)"
	@echo "$(YELLOW)Note: This runs backend + Wails desktop app$(NC)"
	@echo "$(YELLOW)      For web-only frontend, use: make dev-web$(NC)"
	@echo ""
	@$(MAKE) -j2 backend frontend

dev-web: ## Start backend and frontend web server (no desktop window)
	@echo "$(GREEN)Starting web development environment...$(NC)"
	@$(MAKE) -j2 backend frontend-web

backend: setup-venv ## Start backend server (FastAPI)
	@echo "$(GREEN)Starting backend server...$(NC)"
	@echo "$(BLUE)Killing existing process on port 8000...$(NC)"
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		netstat -ano 2>/dev/null | grep :8000 | grep LISTENING | awk '{print $$5}' | xargs -r kill -9 2>/dev/null || \
		taskkill //F //PID $$(netstat -ano 2>/dev/null | grep :8000 | grep LISTENING | awk '{print $$5}') 2>/dev/null || true; \
		sleep 1; \
	else \
		lsof -ti:8000 | xargs kill -9 2>/dev/null || true; \
		sleep 1; \
	fi
	@mkdir -p logs 2>/dev/null || true
	@if [ -d "$(VENV_DIR)" ]; then \
		UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
		if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
			cd backend && ../$(VENV_DIR)/Scripts/python.exe main.py; \
		else \
			cd backend && ../$(VENV_DIR)/bin/python main.py; \
		fi; \
	else \
		cd backend && $(PYTHON) main.py; \
	fi

frontend: check-frontend-deps ## Start Wails desktop app (Go + React + Vite)
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  🚀 Starting Drishti IC Desktop (Wails)$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@# Install bun dependencies if needed
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "$(BLUE)📦 Installing frontend dependencies (bun install)...$(NC)"; \
		cd frontend && bun install; \
		echo "$(GREEN)✓ Frontend dependencies installed$(NC)"; \
	else \
		echo "$(GREEN)✓ Frontend dependencies already installed$(NC)"; \
	fi
	@# Run go mod tidy if go.sum is missing or outdated
	@echo "$(BLUE)📦 Syncing Go dependencies...$(NC)"
	@cd frontend && go mod tidy
	@echo "$(GREEN)✓ Go dependencies synced$(NC)"
	@echo ""
	@echo "$(BLUE)🖥️  Launching Wails development server...$(NC)"
	@echo "$(YELLOW)   This will open a desktop window with HMR enabled$(NC)"
	@echo "$(YELLOW)   Vite dev server runs on port 34115$(NC)"
	@echo ""
	cd frontend && wails dev

frontend-web: check-bun ## Start frontend as web app only (Vite dev server, no desktop window)
	@echo "$(GREEN)Starting frontend web dev server (Vite only)...$(NC)"
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "$(YELLOW)⚠️  Frontend dependencies not installed$(NC)"; \
		echo "$(BLUE)Installing dependencies first...$(NC)"; \
		cd frontend && bun install; \
	fi
	@echo "$(BLUE)Killing existing processes on ports 5173, 34115...$(NC)"
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		for port in 5173 34115; do \
			netstat -ano 2>/dev/null | grep :$$port | grep LISTENING | awk '{print $$5}' | xargs -r kill -9 2>/dev/null || true; \
		done; \
		sleep 1; \
	else \
		for port in 5173 34115; do \
			lsof -ti:$$port | xargs kill -9 2>/dev/null || true; \
		done; \
		sleep 1; \
	fi
	@echo "$(BLUE)Starting Vite dev server...$(NC)"
	cd frontend && bun run dev

frontend-build: check-frontend-deps ## Build Wails desktop app for production
	@echo "$(GREEN)Building Drishti IC Desktop...$(NC)"
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "$(BLUE)📦 Installing frontend dependencies...$(NC)"; \
		cd frontend && bun install; \
	fi
	@echo "$(BLUE)📦 Syncing Go dependencies...$(NC)"
	@cd frontend && go mod tidy
	@echo "$(BLUE)🔨 Building frontend assets...$(NC)"
	@cd frontend && bun run build
	@echo "$(BLUE)🔨 Building desktop binary...$(NC)"
	@cd frontend && wails build
	@echo ""
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)  ✅ Build Complete!$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)Binary location: $(GREEN)frontend/build/bin/$(NC)"
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
		if [ "$$UNAME_S" = "Darwin" ]; then \
		echo "$(BLUE)Run with: $(GREEN)./frontend/build/bin/drishti-ic-desktop$(NC)"; \
	elif [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		echo "$(BLUE)Run with: $(GREEN)frontend\\build\\bin\\drishti-ic-desktop.exe$(NC)"; \
		else \
		echo "$(BLUE)Run with: $(GREEN)./frontend/build/bin/drishti-ic-desktop$(NC)"; \
	fi

install-wails: check-go ## Install Wails CLI
	@echo "$(BLUE)Installing Wails CLI...$(NC)"
	go install github.com/wailsapp/wails/v2/cmd/wails@latest
	@echo ""
	@echo "$(GREEN)✓ Wails CLI installed$(NC)"
	@echo ""
	@echo "$(YELLOW)Make sure Go bin is in your PATH:$(NC)"
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	if [ "$$UNAME_S" = "Darwin" ] || [ "$$UNAME_S" = "Linux" ]; then \
		echo "  $(BLUE)export PATH=\"\$$PATH:\$$(go env GOPATH)/bin\"$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Add this to your ~/.zshrc or ~/.bashrc for persistence$(NC)"; \
	else \
		echo "  Add $(BLUE)%GOPATH%\\bin$(NC) to your PATH environment variable"; \
	fi

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
		UNAME_S=$$(uname -s 2>/dev/null || echo "Windows"); \
		if [ "$$UNAME_S" = "Windows" ] || [ "$$OS" = "Windows_NT" ]; then \
			if py -3.11 --version >nul 2>&1; then \
				echo "$(GREEN)✓ Found Python 3.11, using it for best compatibility$(NC)"; \
				py -3.11 -m venv $(VENV_DIR); \
			elif py -3 --version >nul 2>&1; then \
				PYTHON_VERSION=$$(py -3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' || echo "unknown"); \
				echo "$(YELLOW)⚠️  Python 3.11 not found. Using Python $$PYTHON_VERSION$(NC)"; \
				echo "$(YELLOW)⚠️  For best compatibility, install Python 3.11$(NC)"; \
				py -3 -m venv $(VENV_DIR); \
			elif python --version >nul 2>&1; then \
				PYTHON_VERSION=$$(python --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' || echo "unknown"); \
				echo "$(YELLOW)⚠️  Python 3.11 not found. Using Python $$PYTHON_VERSION$(NC)"; \
				echo "$(YELLOW)⚠️  For best compatibility, install Python 3.11$(NC)"; \
				python -m venv $(VENV_DIR); \
			else \
				echo "$(RED)Error: Python not found!$(NC)"; \
				echo "$(YELLOW)Please install Python 3.11 from: https://www.python.org/downloads/$(NC)"; \
				exit 1; \
			fi; \
			echo "$(BLUE)Upgrading pip...$(NC)"; \
			$(VENV_DIR)/$(VENV_BIN)/python.exe -m pip install --upgrade pip setuptools wheel; \
			echo "$(BLUE)Installing backend dependencies (this may take a few minutes)...$(NC)"; \
			$(VENV_DIR)/$(VENV_BIN)/python.exe -m pip install -r models/requirements.txt || { \
				echo "$(YELLOW)Some packages failed to install. Installing core packages only...$(NC)"; \
				$(VENV_DIR)/$(VENV_BIN)/python.exe -m pip install fastapi uvicorn python-dotenv sqlalchemy alembic opencv-python Pillow pytesseract pdfplumber PyPDF2 numpy requests beautifulsoup4 pydantic pydantic-settings python-multipart psutil; \
				echo "$(YELLOW)Note: Some optional packages skipped due to compatibility issues$(NC)"; \
			}; \
		else \
			if [ -n "$(PYTHON311)" ]; then \
				echo "$(GREEN)✓ Found Python 3.11, using it for best compatibility$(NC)"; \
				$(PYTHON311) -m venv $(VENV_DIR); \
			elif [ -n "$(PYTHON)" ]; then \
				PYTHON_VERSION=$$($(PYTHON) --version 2>&1 | grep -oE '[0-9]+\.[0-9]+'); \
				echo "$(YELLOW)⚠️  Python 3.11 not found. Using Python $$PYTHON_VERSION$(NC)"; \
				if [ "$$UNAME_S" = "Darwin" ]; then \
					echo "$(YELLOW)⚠️  For best compatibility, install Python 3.11: brew install python@3.11$(NC)"; \
				else \
					echo "$(YELLOW)⚠️  For best compatibility, install Python 3.11$(NC)"; \
				fi; \
				$(PYTHON) -m venv $(VENV_DIR); \
			else \
				echo "$(RED)Error: Python not found!$(NC)"; \
				if [ "$$UNAME_S" = "Darwin" ]; then \
					echo "$(YELLOW)Please install Python 3.11: brew install python@3.11$(NC)"; \
				else \
					echo "$(YELLOW)Please install Python 3.11$(NC)"; \
				fi; \
				exit 1; \
			fi; \
			echo "$(BLUE)Upgrading pip...$(NC)"; \
			. $(VENV_DIR)/$(VENV_BIN)/activate && pip install --upgrade pip setuptools wheel; \
			echo "$(BLUE)Installing backend dependencies (this may take a few minutes)...$(NC)"; \
			. $(VENV_DIR)/$(VENV_BIN)/activate && pip install -r models/requirements.txt || { \
				echo "$(YELLOW)Some packages failed to install. Installing core packages only...$(NC)"; \
				. $(VENV_DIR)/$(VENV_BIN)/activate && pip install fastapi uvicorn python-dotenv sqlalchemy alembic opencv-python Pillow pytesseract pdfplumber PyPDF2 numpy requests beautifulsoup4 pydantic pydantic-settings python-multipart psutil; \
				echo "$(YELLOW)Note: Some optional packages skipped due to compatibility issues$(NC)"; \
			}; \
		fi; \
		echo "$(GREEN)✓ Virtual environment created and dependencies installed$(NC)"; \
	fi

down: ## Stop all running services
	@echo "$(YELLOW)Stopping services...$(NC)"
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		taskkill //F //FI "IMAGENAME eq uvicorn.exe" 2>/dev/null || pkill -f uvicorn 2>/dev/null || true; \
		taskkill //F //FI "IMAGENAME eq drishti-ic-desktop.exe" 2>/dev/null || pkill -f "wails dev" 2>/dev/null || true; \
		taskkill //F //FI "IMAGENAME eq node.exe" 2>/dev/null || pkill -f "vite" 2>/dev/null || true; \
	else \
		pkill -f "uvicorn" || true; \
		pkill -f "wails dev" || true; \
		pkill -f "drishti-ic-desktop" || true; \
		pkill -f "vite" || true; \
	fi
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
		UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
		if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
			cd backend && ../$(VENV_DIR)/Scripts/python.exe -c "from models.database import init_database; init_database()"; \
		else \
			cd backend && ../$(VENV_DIR)/bin/python -c "from models.database import init_database; init_database()"; \
		fi; \
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
	rm -rf frontend/dist
	rm -rf frontend/build
	rm -rf frontend/.next
	rm -rf frontend/.turbo
	@echo "$(GREEN)✓ Frontend cleaned$(NC)"
	@echo "$(BLUE)Run 'make frontend' to reinstall and start$(NC)"

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
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	echo "Backend (port 8000):"; \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		netstat -ano 2>/dev/null | grep :8000 | grep LISTENING >/dev/null 2>&1 && echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"; \
	else \
		lsof -ti:8000 >/dev/null 2>&1 && echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"; \
	fi; \
	echo "Frontend Vite (port 34115):"; \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		netstat -ano 2>/dev/null | grep :34115 | grep LISTENING >/dev/null 2>&1 && echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"; \
	else \
		lsof -ti:34115 >/dev/null 2>&1 && echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"; \
	fi; \
	echo "Wails Desktop App:"; \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		tasklist 2>/dev/null | grep -i "drishti-ic-desktop" >/dev/null 2>&1 && echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"; \
	else \
		pgrep -f "drishti-ic-desktop\|wails dev" >/dev/null 2>&1 && echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"; \
	fi

ports: ## Show which ports are in use
	@echo "$(BLUE)Port Usage:$(NC)"
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	echo "Port 8000 (Backend):"; \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		netstat -ano 2>/dev/null | grep :8000 | grep LISTENING || echo "  Not in use"; \
	else \
		lsof -i:8000 || echo "  Not in use"; \
	fi; \
	echo ""; \
	echo "Port 34115 (Wails/Vite Dev Server):"; \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		netstat -ano 2>/dev/null | grep :34115 | grep LISTENING || echo "  Not in use"; \
	else \
		lsof -i:34115 || echo "  Not in use"; \
	fi; \
	echo ""; \
	echo "Port 5173 (Vite standalone):"; \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		netstat -ano 2>/dev/null | grep :5173 | grep LISTENING || echo "  Not in use"; \
	else \
		lsof -i:5173 || echo "  Not in use"; \
	fi

##@ Quick Start

setup: check-frontend-deps install db-migrate ## Complete initial setup
	@echo "$(GREEN)✓ Setup complete! Run 'make dev' to start development.$(NC)"
	@echo "$(BLUE)  • 'make dev' - Start backend + Wails desktop app$(NC)"
	@echo "$(BLUE)  • 'make dev-web' - Start backend + web dev server only$(NC)"
	@echo "$(BLUE)  • 'make frontend' - Start Wails desktop app only$(NC)"

reinstall: clean-venv clean-frontend install ## Reinstall all dependencies from scratch
	@echo "$(GREEN)✓ All dependencies reinstalled$(NC)"

.DEFAULT_GOAL := help
