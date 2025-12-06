#!/bin/bash
set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting API Server..."
echo "📝 Swagger UI: http://localhost:8000/docs"
echo ""

# Navigate to base directory to run module
cd "${BASE_DIR}"

# Run with uvicorn
"${BASE_DIR}/venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 --reload
