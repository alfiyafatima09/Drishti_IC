#!/bin/bash
set -e

# Trap interrupts to kill background processes
trap "kill 0" EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting All Services (Model + API)..."
echo ""

# Check GPU status before starting
if command -v nvidia-smi &> /dev/null; then
    echo "🔍 Pre-flight GPU Check:"
    if nvidia-smi -L &> /dev/null; then
        nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv
        echo ""
    fi
fi

# Start Model Server in background
echo "🤖 Launching Llama Server (with GPU auto-detection)..."
"${SCRIPT_DIR}/scripts/start_llama.sh" &
LLAMA_PID=$!

# Wait for model to initialize (longer wait for GPU initialization)
echo "⏳ Waiting for model to initialize..."
sleep 8

# Check if llama server is still running
if ! kill -0 $LLAMA_PID 2>/dev/null; then
    echo "❌ Llama server failed to start. Check logs above."
    exit 1
fi

# Start API Server
echo ""
echo "⚡ Launching API Server..."
"${SCRIPT_DIR}/start_server.sh"

# Wait for both
wait
