import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ThoughtReach V1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/thoughtreach")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ALLOW_MOCK_EMBEDDINGS: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
