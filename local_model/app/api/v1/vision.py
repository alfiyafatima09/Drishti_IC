import base64
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.vision import VisionRequest, VisionResponse
from app.services.llm import process_vision_request

router = APIRouter()


@router.post("/vision/upload", response_model=VisionResponse)
async def upload_vision(
    prompt: Annotated[str, Form(...)],
    image: Annotated[UploadFile, File(...)],
    max_tokens: Annotated[int, Form()] = 512,
    temperature: Annotated[float, Form()] = 0.7,
) -> VisionResponse:
    try:
        # Read and encode image
        image_bytes = await image.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        request_data = VisionRequest(
            prompt=prompt,
            image_base64=image_base64,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return process_vision_request(request_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
