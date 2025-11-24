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

.PHONY: help install dev backend frontend down clean fmt lint logs db-migrate db-reset docker-build docker-up docker-down contracts-lint contracts-gen

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

dev: ## Start both backend and frontend in parallel
	@echo "$(GREEN)Starting development environment...$(NC)"
	@$(MAKE) -j2 backend frontend-ngrok

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

frontend-no-ngrok: check-node ## Start frontend dev server (Next.js)
	@echo "$(GREEN)Starting frontend server...$(NC)"
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "$(YELLOW)⚠️  Frontend dependencies not installed$(NC)"; \
		echo "$(BLUE)Installing dependencies first...$(NC)"; \
		cd frontend && npm install; \
	fi
	@echo "$(BLUE)Killing existing processes on ports 3000-3003...$(NC)"
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		for port in 3000 3001 3002 3003; do \
			netstat -ano 2>/dev/null | grep :$$port | grep LISTENING | awk '{print $$5}' | xargs -r kill -9 2>/dev/null || \
			taskkill //F //PID $$(netstat -ano 2>/dev/null | grep :$$port | grep LISTENING | awk '{print $$5}') 2>/dev/null || true; \
		done; \
		sleep 1; \
	else \
		for port in 3000 3001 3002 3003; do \
			lsof -ti:$$port | xargs kill -9 2>/dev/null || true; \
		done; \
		sleep 1; \
	fi
	@echo "$(BLUE)Using default config: API at http://localhost:8000$(NC)"
	@$(MAKE) show-network-urls &
	cd frontend && npm run dev

frontend: ## Start frontend with ngrok tunnel (for public access)
	@echo "$(GREEN)Starting frontend with ngrok tunnel...$(NC)"
	@echo "$(YELLOW)⚠️  Important: Backend will run on localhost:8000$(NC)"
	@echo "$(YELLOW)   Make sure your device can reach localhost or use network IP$(NC)"
	@echo ""
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	TEMP_DIR=$$([ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ] && echo "$$TEMP" || echo "/tmp"); \
	if ! command -v ngrok >/dev/null 2>&1; then \
		echo "$(RED)✗ ngrok not found!$(NC)"; \
		echo "$(YELLOW)Install ngrok:$(NC)"; \
		if [ "$$UNAME_S" = "Darwin" ]; then \
			echo "  macOS: $(BLUE)brew install ngrok/ngrok/ngrok$(NC)"; \
		else \
			echo "  Download from: $(BLUE)https://ngrok.com/download$(NC)"; \
		fi; \
		exit 1; \
	fi
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	TEMP_DIR=$$([ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ] && echo "$$TEMP" || echo "/tmp"); \
	echo "$(BLUE)Killing existing ngrok tunnels...$(NC)"; \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		taskkill //F //FI "IMAGENAME eq ngrok.exe" 2>/dev/null || pkill -f ngrok 2>/dev/null || true; \
	else \
		pkill -f ngrok || true; \
	fi; \
	sleep 2
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	TEMP_DIR=$$([ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ] && echo "$$TEMP" || echo "/tmp"); \
	echo "$(BLUE)Killing existing processes on ports 3000-3003...$(NC)"; \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		for port in 3000 3001 3002 3003; do \
			netstat -ano 2>/dev/null | grep :$$port | grep LISTENING | awk '{print $$5}' | xargs -r kill -9 2>/dev/null || \
			taskkill //F //PID $$(netstat -ano 2>/dev/null | grep :$$port | grep LISTENING | awk '{print $$5}') 2>/dev/null || true; \
		done; \
	else \
		for port in 3000 3001 3002 3003; do \
			lsof -ti:$$port | xargs kill -9 2>/dev/null || true; \
		done; \
	fi; \
	sleep 1
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	TEMP_DIR=$$([ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ] && echo "$$TEMP" || echo "/tmp"); \
	echo "$(BLUE)Starting frontend server first...$(NC)"; \
	cd frontend && npm run dev > "$$TEMP_DIR/nextjs.log" 2>&1 & \
	sleep 8
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		FRONTEND_PORT=$$(netstat -ano 2>/dev/null | grep :300 | grep LISTENING | head -1 | awk '{print $$4}' | cut -d: -f2 || echo "3000"); \
	else \
		FRONTEND_PORT=$$(lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -E ':(300[0-9]|3000)' | grep node | head -1 | awk '{print $$9}' | cut -d: -f2 | head -1); \
		if [ -z "$$FRONTEND_PORT" ]; then \
			FRONTEND_PORT=$$(netstat -an 2>/dev/null | grep LISTEN | grep -E '\.(300[0-9]|3000)' | head -1 | awk '{print $$4}' | cut -d: -f2 | cut -d. -f1); \
		fi; \
	fi; \
	if [ -z "$$FRONTEND_PORT" ]; then \
		FRONTEND_PORT="3000"; \
	fi; \
	UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	TEMP_DIR=$$([ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ] && echo "$$TEMP" || echo "/tmp"); \
	PYTHON_CMD=$$(command -v python3 2>/dev/null || command -v python 2>/dev/null || command -v py 2>/dev/null || echo "python3"); \
	echo "$(BLUE)Starting ngrok tunnel on port $$FRONTEND_PORT...$(NC)"; \
	ngrok http $$FRONTEND_PORT --log=stdout > "$$TEMP_DIR/ngrok.log" 2>&1 & \
	sleep 5
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	TEMP_DIR=$$([ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ] && echo "$$TEMP" || echo "/tmp"); \
	PYTHON_CMD=$$(command -v python3 2>/dev/null || command -v python 2>/dev/null || command -v py 2>/dev/null || echo "python3"); \
	echo "$(BLUE)Waiting for ngrok to start and fetch public URL...$(NC)"; \
	NGROK_URL=""; \
	for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do \
		echo -n "$(BLUE)Attempt $$i/15...$(NC)\r"; \
		NGROK_RESPONSE=$$(curl -s http://localhost:4040/api/tunnels 2>/dev/null); \
		if [ -n "$$NGROK_RESPONSE" ]; then \
			NGROK_URL=$$(echo "$$NGROK_RESPONSE" | $$PYTHON_CMD -c "import sys, json; data=json.load(sys.stdin); tunnels=data.get('tunnels', []); print(tunnels[0]['public_url'] if tunnels else '')" 2>/dev/null); \
			if [ -z "$$NGROK_URL" ]; then \
				NGROK_URL=$$(echo "$$NGROK_RESPONSE" | grep -oE '"public_url":"https://[^"]*' | head -1 | sed 's/"public_url":"//'); \
			fi; \
			if [ -z "$$NGROK_URL" ]; then \
				NGROK_URL=$$(echo "$$NGROK_RESPONSE" | grep -oE 'https://[a-z0-9-]+\.ngrok-free\.app' | head -1); \
			fi; \
			if [ -z "$$NGROK_URL" ]; then \
				NGROK_URL=$$(echo "$$NGROK_RESPONSE" | grep -oE 'https://[a-z0-9-]+\.ngrok\.io' | head -1); \
			fi; \
		fi; \
		if [ -n "$$NGROK_URL" ]; then \
			break; \
		fi; \
		sleep 2; \
	done; \
	echo ""; \
	if [ -z "$$NGROK_URL" ]; then \
		echo "$(YELLOW)⚠️  Still waiting for ngrok URL... Trying one more time with longer wait...$(NC)"; \
		sleep 5; \
		NGROK_RESPONSE=$$(curl -s http://localhost:4040/api/tunnels 2>/dev/null); \
		if [ -n "$$NGROK_RESPONSE" ]; then \
			NGROK_URL=$$(echo "$$NGROK_RESPONSE" | $$PYTHON_CMD -c "import sys, json; data=json.load(sys.stdin); tunnels=data.get('tunnels', []); print(tunnels[0]['public_url'] if tunnels else '')" 2>/dev/null); \
			if [ -z "$$NGROK_URL" ]; then \
				NGROK_URL=$$(echo "$$NGROK_RESPONSE" | grep -oE '"public_url":"https://[^"]*' | head -1 | sed 's/"public_url":"//'); \
			fi; \
			if [ -z "$$NGROK_URL" ]; then \
				NGROK_URL=$$(echo "$$NGROK_RESPONSE" | grep -oE 'https://[a-z0-9-]+\.ngrok-free\.app' | head -1); \
			fi; \
			if [ -z "$$NGROK_URL" ]; then \
				NGROK_URL=$$(echo "$$NGROK_RESPONSE" | grep -oE 'https://[a-z0-9-]+\.ngrok\.io' | head -1); \
			fi; \
		fi; \
	fi; \
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
		echo ""; \
		echo "$(BLUE)📋 Quick Actions:$(NC)"; \
		UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
		if [ "$$UNAME_S" = "Darwin" ]; then \
			echo "  • Open in browser: $(GREEN)open $$NGROK_URL_SKIP$(NC)"; \
		elif [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
			echo "  • Open in browser: $(GREEN)start $$NGROK_URL_SKIP$(NC)"; \
		else \
			echo "  • Open in browser: $(GREEN)xdg-open $$NGROK_URL_SKIP$(NC)"; \
		fi; \
		echo "  • Ngrok dashboard: $(GREEN)http://localhost:4040$(NC)"; \
		echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"; \
		echo ""; \
		UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
		if [ "$$UNAME_S" = "Darwin" ] && command -v open >/dev/null 2>&1; then \
			echo "$(BLUE)Opening ngrok URL in browser...$(NC)"; \
			open "$$NGROK_URL_SKIP" 2>/dev/null || true; \
		elif ([ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]) && command -v start >/dev/null 2>&1; then \
			echo "$(BLUE)Opening ngrok URL in browser...$(NC)"; \
			start "$$NGROK_URL_SKIP" 2>/dev/null || true; \
		elif [ "$$UNAME_S" = "Linux" ] && command -v xdg-open >/dev/null 2>&1; then \
			echo "$(BLUE)Opening ngrok URL in browser...$(NC)"; \
			xdg-open "$$NGROK_URL_SKIP" 2>/dev/null || true; \
		fi; \
	else \
		echo ""; \
		echo "$(YELLOW)⚠️  Could not automatically fetch ngrok URL$(NC)"; \
		echo "$(BLUE)Please check ngrok dashboard manually:$(NC)"; \
		echo "  $(GREEN)http://localhost:4040$(NC)"; \
		echo ""; \
		UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
		TEMP_DIR=$$([ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ] && echo "$$TEMP" || echo "/tmp"); \
		PYTHON_CMD=$$(command -v python3 2>/dev/null || command -v python 2>/dev/null || command -v py 2>/dev/null || echo "python3"); \
		echo "$(BLUE)Or check logs:$(NC)"; \
		echo "  $(YELLOW)tail -f $$TEMP_DIR/ngrok.log$(NC)  # Ngrok logs"; \
		echo "  $(YELLOW)tail -f $$TEMP_DIR/nextjs.log$(NC)  # Frontend logs"; \
		echo ""; \
		echo "$(BLUE)You can also try fetching the URL manually:$(NC)"; \
		echo "  $(GREEN)curl -s http://localhost:4040/api/tunnels | $$PYTHON_CMD -m json.tool$(NC)"; \
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
		taskkill //F //FI "IMAGENAME eq node.exe" //FI "WINDOWTITLE eq *next*" 2>/dev/null || pkill -f "next dev" 2>/dev/null || true; \
	else \
		pkill -f "uvicorn" || true; \
		pkill -f "next dev" || true; \
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
	@UNAME_S=$$(uname -s 2>/dev/null || echo "Unknown"); \
	echo "Backend (port 8000):"; \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		netstat -ano 2>/dev/null | grep :8000 | grep LISTENING >/dev/null 2>&1 && echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"; \
	else \
		lsof -ti:8000 >/dev/null 2>&1 && echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"; \
	fi; \
	echo "Frontend (port 3000):"; \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		netstat -ano 2>/dev/null | grep :3000 | grep LISTENING >/dev/null 2>&1 && echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"; \
	else \
		lsof -ti:3000 >/dev/null 2>&1 && echo "  $(GREEN)✓ Running$(NC)" || echo "  $(RED)✗ Not running$(NC)"; \
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
	echo "Port 3000 (Frontend):"; \
	if [ "$$UNAME_S" = "MINGW"* ] || [ "$$UNAME_S" = "MSYS"* ] || [ "$$OS" = "Windows_NT" ]; then \
		netstat -ano 2>/dev/null | grep :3000 | grep LISTENING || echo "  Not in use"; \
	else \
		lsof -i:3000 || echo "  Not in use"; \
	fi

##@ Quick Start

setup: check-node install db-migrate ## Complete initial setup
	@echo "$(GREEN)✓ Setup complete! Run 'make dev' to start development.$(NC)"

reinstall: clean-venv clean-frontend install ## Reinstall all dependencies from scratch
	@echo "$(GREEN)✓ All dependencies reinstalled$(NC)"

.DEFAULT_GOAL := help
