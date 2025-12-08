#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting API Server..."
echo "📝 Endpoint: http://localhost:8001/api/v1/vision/upload"

# Run with reload for development
"${SCRIPT_DIR}/venv/bin/uvicorn" main:app --host 0.0.0.0 --port 8001 --reload --app-dir "${SCRIPT_DIR}"
