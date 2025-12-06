# Service layer for interacting with the Llama model server
import requests
import logging
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class LlamaService:
    @staticmethod
    def generate_completion(messages: list, max_tokens: int = 512, temperature: float = 0.7) -> Dict[str, Any]:
        """Send a completion request to the llama-server."""
        try:
            payload = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(
                settings.LLAMA_SERVER_URL,
                json=payload,
                timeout=settings.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with llama-server: {str(e)}")
            raise Exception(f"Model server error: {str(e)}")

llama_service = LlamaService()
