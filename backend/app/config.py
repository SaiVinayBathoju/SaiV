"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "SaiV API"
    debug: bool = False

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_anon_key: str = ""

    # OpenAI (optional)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_fallback_to_local: bool = True

    # Google Gemini - free tier (get key at https://aistudio.google.com/apikey)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # AI provider for chat/flashcards/quiz: "openai" | "gemini" | "auto" (auto = try OpenAI, then Gemini)
    ai_provider: str = "auto"

    # Processing limits
    max_pdf_pages: int = 100
    max_chunk_size: int = 512
    chunk_overlap: int = 50
    max_retrieval_chunks: int = 5

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
