from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    # Llama server URL for handling chat completions
    LLAMA_SERVER_URL: str = "http://localhost:8080/v1/chat/completions"
    MODEL_NAME: str = "qwen3-vl-8b"
    # Timeout for requests to the LLM
    REQUEST_TIMEOUT: int = 300


settings = Settings()
