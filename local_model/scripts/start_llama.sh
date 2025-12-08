#!/bin/bash
set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Settings
HOST="0.0.0.0"
PORT="8080"
CONTEXT_SIZE="4096"

# Auto-detect CUDA and GPU
echo "🔍 Detecting GPU and CUDA..."

# Check for nvidia-smi
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA drivers found"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1
else
    echo "⚠️  nvidia-smi not found, checking for CUDA..."
fi

# Auto-detect CUDA installation
CUDA_PATHS=(
    "/usr/local/cuda"
    "/usr/local/cuda-12.6"
    "/usr/local/cuda-12.5"
    "/usr/local/cuda-12.4"
    "/usr/local/cuda-12.3"
    "/usr/local/cuda-12.2"
    "/usr/local/cuda-12.1"
    "/usr/local/cuda-12.0"
    "/usr/local/cuda-11.8"
    "/opt/cuda"
)

CUDA_FOUND=false
for CUDA_PATH in "${CUDA_PATHS[@]}"; do
    if [ -d "$CUDA_PATH" ]; then
        echo "✅ Found CUDA at: $CUDA_PATH"
        export PATH="$CUDA_PATH/bin:$PATH"
        export LD_LIBRARY_PATH="$CUDA_PATH/lib64:$LD_LIBRARY_PATH"
        CUDA_FOUND=true
        break
    fi
done

# Also check common system CUDA locations
if [ "$CUDA_FOUND" = false ]; then
    if [ -d "/usr/lib/cuda" ]; then
        echo "✅ Found system CUDA at: /usr/lib/cuda"
        export LD_LIBRARY_PATH="/usr/lib/cuda/lib64:$LD_LIBRARY_PATH"
        CUDA_FOUND=true
    fi
fi

# Set GPU layers based on availability
# For Qwen3-VL 8B model, use 32 layers on GPU (rest on CPU for hybrid mode)
GPU_LAYERS="0"  # Default to CPU

# Check GPU availability
GPU_ACCESSIBLE=false
GPU_INFO_AVAILABLE=false

if command -v nvidia-smi &> /dev/null; then
    # Try to get GPU info
    if nvidia-smi -L &> /dev/null 2>&1; then
        GPU_ACCESSIBLE=true
        GPU_INFO_AVAILABLE=true
        GPU_COUNT=$(nvidia-smi -L 2>/dev/null | wc -l)
        GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
        GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1)
        
        echo "✅ GPU Detected:"
        echo "   - Count: ${GPU_COUNT}"
        echo "   - Name: ${GPU_NAME}"
        echo "   - Memory: ${GPU_MEMORY}"
    else
        # nvidia-smi exists but can't communicate - driver might not be loaded
        GPU_ERROR=$(nvidia-smi -L 2>&1)
        if echo "$GPU_ERROR" | grep -q "couldn't communicate"; then
            echo "⚠️  NVIDIA driver communication issue"
            echo "   nvidia-smi found but can't communicate with driver"
            echo ""
            
            # Check for Secure Boot
            if command -v mokutil &> /dev/null; then
                SB_STATE=$(mokutil --sb-state 2>/dev/null | grep -i "enabled" || echo "")
                if [ -n "$SB_STATE" ]; then
                    echo "   🔒 Secure Boot is ENABLED - this is blocking the NVIDIA driver"
                    echo ""
                    echo "   💡 To enable GPU acceleration:"
                    echo "      1. Reboot and enter BIOS/UEFI (usually F2, F10, F12, or Del)"
                    echo "      2. Find 'Secure Boot' option and DISABLE it"
                    echo "      3. Save and reboot"
                    echo "      4. Then run: sudo modprobe nvidia"
                    echo ""
                    echo "   ⚠️  For now, continuing in CPU mode (will work, just slower)"
                else
                    echo "   💡 Try these commands to fix:"
                    echo "      sudo modprobe nvidia"
                    echo "      sudo systemctl restart nvidia-persistenced"
                    echo "      # Or reboot your system"
                fi
            else
                echo "   💡 Try these commands to fix:"
                echo "      sudo modprobe nvidia"
                echo "      sudo systemctl restart nvidia-persistenced"
                echo "      # Or reboot your system"
            fi
            echo ""
            # If CUDA is found, still try GPU - the binary might work even if nvidia-smi doesn't
            if [ "$CUDA_FOUND" = true ]; then
                GPU_ACCESSIBLE=true
                echo "   ⚠️  CUDA found - will attempt GPU anyway (llama-server may work)"
                echo "   ⚠️  If GPU init fails, it will automatically fallback to CPU"
            fi
        fi
    fi
fi

# Set GPU layers if CUDA found and GPU should be accessible
if [ "$CUDA_FOUND" = true ] && [ "$GPU_ACCESSIBLE" = true ]; then
    # Optimize GPU layers based on available VRAM (in MiB)
    # Note: Vision model (CLIP) needs ~1100 MiB, so we need to reserve space for it
    if [ "$GPU_INFO_AVAILABLE" = true ]; then
        # Extract GPU memory in MiB (first number from "6141 MiB")
        GPU_MEM_MIB=$(echo "$GPU_MEMORY" | grep -oE '[0-9]+' | head -1)
        if [ -n "$GPU_MEM_MIB" ]; then
            # Memory breakdown for vision model:
            # - Vision model (CLIP): ~1100 MiB
            # - KV cache: ~512 MiB  
            # - Compute buffers: ~800 MiB
            # - Per model layer: ~109 MiB
            # Available for model layers: VRAM - 2400 MiB
            if [ "$GPU_MEM_MIB" -ge 10000 ]; then
                GPU_LAYERS="32"  # Full GPU for 10GB+
            elif [ "$GPU_MEM_MIB" -ge 8000 ]; then
                GPU_LAYERS="28"  # For 8GB GPUs
            elif [ "$GPU_MEM_MIB" -ge 6000 ]; then
                GPU_LAYERS="18"  # For 6GB GPUs (RTX 4050) - conservative
            elif [ "$GPU_MEM_MIB" -ge 4000 ]; then
                GPU_LAYERS="12"  # For 4GB GPUs
            else
                GPU_LAYERS="8"   # Conservative for <4GB
            fi
        else
            GPU_LAYERS="18"  # Safe default
        fi
        echo "🚀 GPU Mode: Using ${GPU_LAYERS} layers on GPU (hybrid with CPU)"
        echo "   💾 GPU Memory: ${GPU_MEM_MIB} MiB"
        echo "   📊 Memory estimate:"
        echo "      - Model layers (~${GPU_LAYERS}): ~$((GPU_LAYERS * 109)) MiB"
        echo "      - Vision model: ~1100 MiB"
        echo "      - KV cache & buffers: ~1300 MiB"
        echo "      - Total: ~$((GPU_LAYERS * 109 + 2400)) MiB"
    else
        GPU_LAYERS="18"  # Safe default for unknown VRAM
        echo "🚀 Attempting GPU Mode: ${GPU_LAYERS} layers"
        echo "   ⚠️  Note: Driver issue detected - will try GPU but may fallback to CPU"
    fi
elif [ "$CUDA_FOUND" = false ]; then
    echo "⚠️  CUDA not found - using CPU mode"
    GPU_LAYERS="0"
else
    echo "⚠️  GPU not accessible - using CPU mode"
    echo "   ℹ️  System will work fine in CPU mode (slower but functional)"
    GPU_LAYERS="0"
fi

# Allow override via environment variable
if [ -n "$LLAMA_GPU_LAYERS" ]; then
    GPU_LAYERS="$LLAMA_GPU_LAYERS"
    echo "📝 Using GPU layers from environment: ${GPU_LAYERS}"
fi

# Setup library paths
export LD_LIBRARY_PATH="${BASE_DIR}/lib:$LD_LIBRARY_PATH"

echo ""
echo "🚀 Starting Qwen3-VL Model Server..."
echo "📍 Model Path: ${BASE_DIR}/models/qwen3-vl-8b-instruct-q4_k_m.gguf"
echo "🔧 GPU Layers: ${GPU_LAYERS} (0 = CPU only, >0 = GPU accelerated)"
echo "🌐 Server URL: http://${HOST}:${PORT}"
echo ""

# Build command
CMD=(
    "${BASE_DIR}/bin/llama-server"
    -m "${BASE_DIR}/models/qwen3-vl-8b-instruct-q4_k_m.gguf"
    --mmproj "${BASE_DIR}/models/qwen3-8b-mmproj.gguf"
    --host "${HOST}"
    --port "${PORT}"
    -c "${CONTEXT_SIZE}"
)

# Add GPU layers only if > 0
if [ "$GPU_LAYERS" -gt 0 ]; then
    CMD+=(-ngl "${GPU_LAYERS}")
    echo "✅ Attempting GPU acceleration (${GPU_LAYERS} layers)"
    echo "   Note: If GPU init fails, it will automatically fallback to CPU"
else
    echo "ℹ️  Running in CPU mode"
fi

echo ""
echo "🚀 Starting server..."
echo ""

# Run server
# Note: If GPU fails, llama-server will automatically fallback to CPU
"${CMD[@]}"
