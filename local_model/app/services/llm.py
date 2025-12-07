import requests

from app.core.config import settings
from app.core.prompts import IC_ANALYSIS_PROMPT
from app.schemas.vision import VisionRequest, VisionResponse


def process_vision_request(request: VisionRequest) -> VisionResponse:
    # Construct the full prompt with system instructions
    full_prompt = f"{IC_ANALYSIS_PROMPT}\n\nUser Request: {request.prompt}"

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": full_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{request.image_base64}"
                        },
                    },
                ],
            }
        ],
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
    }

    try:
        response = requests.post(
            settings.LLAMA_SERVER_URL, json=payload, timeout=settings.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]

        return VisionResponse(response=content, model=settings.MODEL_NAME)
    except Exception as e:
        # Let the router handle the exception or re-raise
        raise e
