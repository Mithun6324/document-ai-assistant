from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Document AI Assistant"
    debug: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    database_url: str = "postgresql://docai:docai@localhost:5432/docai"

    jwt_secret: str = "change-me-to-a-long-random-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    llm_provider: str = "gemini"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    chroma_persist_dir: str = "./chroma_data"
    chroma_collection: str = "document_chunks"

    upload_dir: str = "./uploads"
    max_file_size_mb: int = 25

    top_k: int = 5
    retrieval_candidates: int = 20
    similarity_threshold: float = 0.35
    max_context_tokens: int = 6000
    max_chunk_size: int = 1200
    chunk_overlap: int = 80

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
