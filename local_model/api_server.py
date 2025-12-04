#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import base64
from typing import Optional
import uvicorn

app = FastAPI(title="Qwen3-VL API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LLAMA_SERVER_URL = "http://localhost:8080/v1/chat/completions"

class TextRequest(BaseModel):
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7

class ImageRequest(BaseModel):
    prompt: str
    image_base64: str
    max_tokens: int = 512
    temperature: float = 0.7

@app.get("/")
def root():
    return {"status": "online", "model": "qwen3-vl-8b"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/chat")
def chat(request: TextRequest):
    try:
        response = requests.post(
            LLAMA_SERVER_URL,
            json={
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": request.max_tokens,
                "temperature": request.temperature
            },
            timeout=300
        )
        response.raise_for_status()
        data = response.json()
        return {
            "response": data["choices"][0]["message"]["content"],
            "model": "qwen3-vl-8b"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vision")
def vision(request: ImageRequest):
    try:
        response = requests.post(
            LLAMA_SERVER_URL,
            json={
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": request.prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{request.image_base64}"}}
                    ]
                }],
                "max_tokens": request.max_tokens,
                "temperature": request.temperature
            },
            timeout=300
        )
        response.raise_for_status()
        data = response.json()
        return {
            "response": data["choices"][0]["message"]["content"],
            "model": "qwen3-vl-8b"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vision/upload")
async def vision_upload(
    prompt: str = Form(...),
    image: UploadFile = File(...),
    max_tokens: int = Form(512),
    temperature: float = Form(0.7)
):
    try:
        image_bytes = await image.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        response = requests.post(
            LLAMA_SERVER_URL,
            json={
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }],
                "max_tokens": max_tokens,
                "temperature": temperature
            },
            timeout=300
        )
        response.raise_for_status()
        data = response.json()
        return {
            "response": data["choices"][0]["message"]["content"],
            "model": "qwen3-vl-8b"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

