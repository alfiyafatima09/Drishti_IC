# Qwen3-VL Local API

Local quantized vision model for IC chip analysis. Uses Qwen3-VL-8B model running locally.

## How to Run

### Step 1: Start Model Server (Terminal 1)
```bash
./start.sh
```
Wait until you see: "server is listening on http://0.0.0.0:8080"

### Step 2: Start API Server (Terminal 2)
```bash
./start_api.sh
```

The API server will be available at: `http://localhost:8000`

## Testing with Ngrok (Remote Access)

To allow teammates to test the API remotely:

### Step 3: Start Ngrok Tunnel (Terminal 3)
```bash
ngrok http 8000
```

This will give you a public HTTPS URL like: `https://abc123.ngrok-free.app`

Share this URL with teammates so they can test the API remotely.

**Note:** Your model and API server must stay running for teammates to access it via ngrok.

## API Endpoints

Base URL: `http://localhost:8000` (or your ngrok URL)

### 1. GET /health
Health check endpoint

### 2. POST /api/chat
Text only chat

**Example:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is an integrated circuit?", "max_tokens": 512}'
```

### 3. POST /api/vision
Image analysis with base64 encoded image

### 4. POST /api/vision/upload
Image upload (multipart/form-data) - **Recommended**

**Example:**
```bash
curl -X POST http://localhost:8000/api/vision/upload \
  -F "prompt=Count the number of pins on this IC chip." \
  -F "image=@ic_images/ic_1.jpeg" \
  -F "max_tokens=1024" \
  -F "temperature=0.7"
```

## Test Images

Test images are available in `ic_images/` directory (collected by Yuktha).

## Requirements

- Python 3.12+
- CUDA 12.6 (for GPU acceleration) or CPU mode
- Model binaries and libraries (included in repo)

Install Python dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Notes

- CORS enabled for all origins
- Model runs locally - no external API calls
- Supports both GPU and CPU inference
