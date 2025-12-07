from pydantic import BaseModel


class VisionRequest(BaseModel):
    prompt: str
    image_base64: str
    max_tokens: int = 512
    temperature: float = 0.7


class VisionResponse(BaseModel):
    response: str  # The raw text response from the model
    model: str
