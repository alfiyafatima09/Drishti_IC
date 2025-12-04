#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set library path to include our local libs
export LD_LIBRARY_PATH="${SCRIPT_DIR}/lib:$LD_LIBRARY_PATH"

# Set CUDA paths (required for GPU)
export PATH="/usr/local/cuda-12.6/bin:$PATH"
export LD_LIBRARY_PATH="/usr/local/cuda-12.6/lib64:$LD_LIBRARY_PATH"

echo "🚀 Starting Qwen3-VL API Server..."
echo "📍 Models: ${SCRIPT_DIR}/models/"
echo "🔧 GPU Layers: 22"
echo "📊 Context Size: 4096"
echo "🌐 Server URL: http://localhost:8080"
echo ""

# Start the server
"${SCRIPT_DIR}/bin/llama-server" \
    -m "${SCRIPT_DIR}/models/qwen3-vl-8b-instruct-q4_k_m.gguf" \
    --mmproj "${SCRIPT_DIR}/models/qwen3-8b-mmproj.gguf" \
    --host 0.0.0.0 \
    --port 8080 \
    -c 4096 \
    -ngl 22

