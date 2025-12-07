#!/bin/bash
set -e

# Trap interrupts to kill background processes
trap "kill 0" EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting All Services (Model + API)..."

# Start Model Server in background
echo "🤖 Launching Llama Server..."
"${SCRIPT_DIR}/scripts/start_llama.sh" &
LLAMA_PID=$!

# Wait a few seconds for model to initialize (optional but helpful)
sleep 5

# Start API Server
echo "⚡ Launching API Server..."
"${SCRIPT_DIR}/start_server.sh"

# Wait for both
wait
