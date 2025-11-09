from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration (Optional - not used with ChromaDB default embeddings)
    openai_api_key: Optional[str] = None

    # ChromaDB Configuration
    chroma_db_path: str = "./chroma_db"

    # File Upload Configuration
    upload_dir: str = "./storage/uploads"
    max_file_size: int = 52428800  # 50MB in bytes

    # Allowed file types
    allowed_extensions: list[str] = ["pdf", "pptx"]

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"

    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Job Configuration
    job_ttl: int = 86400  # 24 hours in seconds

    # Database Configuration
    db_path: str = "./app/data/quizzes.db"
    
    # Groq AI Configuration
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.1-8b-instant"
    
    # Quiz Configuration
    max_questions_per_quiz: int = 20
    max_content_chunks: int = 15
    
    # Vector DB Security Settings
    vector_db_similarity_threshold: float = 0.6  # Minimum similarity score (0.0-1.0)
    vector_db_min_results: int = 3  # Minimum documents required to generate quiz

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
