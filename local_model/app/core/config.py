from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8001  # Changed from 8000 to match backend expectation
    # Llama server URL for handling chat completions
    LLAMA_SERVER_URL: str = "http://localhost:8080/v1/chat/completions"
    MODEL_NAME: str = "qwen3-vl-8b"
    # Reduced timeout for faster processing
    REQUEST_TIMEOUT: int = 60  # Reduced from 300 seconds


settings = Settings()
