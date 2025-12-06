# Pydantic models for API request and response validation
from pydantic import BaseModel
from typing import Optional

class TextRequest(BaseModel):
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7

class ImageRequest(BaseModel):
    prompt: str
    image_base64: str
    max_tokens: int = 512
    temperature: float = 0.7

class APIResponse(BaseModel):
    response: str
    model: str
