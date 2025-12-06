# API router for vision-language tasks including multipart uploads
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.schemas import ImageRequest, APIResponse
from app.services.llama import llama_service
from app.config import settings
import base64

router = APIRouter()

@router.post("/vision", response_model=APIResponse)
async def vision(request: ImageRequest):
    try:
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": request.prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{request.image_base64}"}}
            ]
        }]
        
        data = llama_service.generate_completion(
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        return APIResponse(
            response=data["choices"][0]["message"]["content"],
            model=settings.MODEL_NAME
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vision/upload", response_model=APIResponse)
async def vision_upload(
    prompt: str = Form(...),
    image: UploadFile = File(...),
    max_tokens: int = Form(512),
    temperature: float = Form(0.7)
):
    try:
        image_bytes = await image.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Re-use vision logic
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            ]
        }]
        
        data = llama_service.generate_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return APIResponse(
            response=data["choices"][0]["message"]["content"],
            model=settings.MODEL_NAME
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
