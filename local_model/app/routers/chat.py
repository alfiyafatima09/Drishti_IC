# API router for text-based chat completions
from fastapi import APIRouter, HTTPException
from app.schemas import TextRequest, APIResponse
from app.services.llama import llama_service
from app.config import settings

router = APIRouter()

@router.post("/chat", response_model=APIResponse)
async def chat(request: TextRequest):
    try:
        messages = [{"role": "user", "content": request.prompt}]
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
