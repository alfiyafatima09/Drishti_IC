#!/bin/bash
set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Settings - Optimized for RTX 4050 with vision model
HOST="0.0.0.0"
PORT="8080"
CONTEXT_SIZE="8192"  # Increased for image processing
GPU_LAYERS="0"     # Use CPU only for RTX 4050 (limited VRAM)
THREADS="4"         # Reduced CPU threads

echo "🚀 Starting Qwen3-VL Model Server (Optimized)..."
echo "📍 Model Path: ${BASE_DIR}/models/qwen3-vl-8b-instruct-q4_k_m.gguf"
echo "🔧 GPU Layers: ${GPU_LAYERS}"
echo "🧵 CPU Threads: ${THREADS}"
echo "🌐 Server URL: http://${HOST}:${PORT}"
echo ""

# Setup environment
export LD_LIBRARY_PATH="${BASE_DIR}/lib:$LD_LIBRARY_PATH"
export PATH="/usr/local/cuda-12.6/bin:$PATH"
export LD_LIBRARY_PATH="/usr/local/cuda-12.6/lib64:$LD_LIBRARY_PATH"

# Run server with optimizations
"${BASE_DIR}/bin/llama-server" \
    -m "${BASE_DIR}/models/qwen3-vl-8b-instruct-q4_k_m.gguf" \
    --mmproj "${BASE_DIR}/models/qwen3-8b-mmproj.gguf" \
    --host "${HOST}" \
    --port "${PORT}" \
    -c "${CONTEXT_SIZE}" \
    -ngl "${GPU_LAYERS}" \
    --threads "${THREADS}" \
    --mlock \
    --no-mmap \
    --flash-attn auto \
    --batch-size 256 \
    --ubatch-size 256
