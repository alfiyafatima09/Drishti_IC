# Application configuration settings using Pydantic
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TITLE: str = "Qwen3-VL API"
    VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LLAMA_SERVER_URL: str = "http://localhost:8080/v1/chat/completions"
    MODEL_NAME: str = "qwen3-vl-8b"
    REQUEST_TIMEOUT: int = 300

    class Config:
        env_file = ".env"

settings = Settings()
