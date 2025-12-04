#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting API Server on port 8000..."
echo "📝 Endpoints:"
echo "   - http://localhost:8000/api/chat (text)"
echo "   - http://localhost:8000/api/vision (base64 image)"
echo "   - http://localhost:8000/api/vision/upload (file upload)"
echo ""

"${SCRIPT_DIR}/venv/bin/python" "${SCRIPT_DIR}/api_server.py"

