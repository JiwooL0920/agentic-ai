"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars
    )

    # Application
    app_name: str = "Agentic AI Platform"
    debug: bool = False
    environment: str = "development"

    # Blueprints
    blueprints_path: str = "blueprints"
    default_blueprint: str = "devassist"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:32b"
    ollama_embedding_model: str = "nomic-embed-text"

    # ScyllaDB (Alternator - DynamoDB-compatible API)
    # Note: Currently configured for LocalStack DynamoDB
    # SECURITY: These are LocalStack development defaults - override via environment
    # variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) in production
    scylladb_endpoint: str = "http://localstack.localstack.svc.cluster.local:4566"
    aws_region: str = "us-east-1"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"

    # PostgreSQL (pgvector - RAG only)
    # SECURITY: Set POSTGRES_PASSWORD environment variable in production
    postgres_host: str = "postgres-rw.database.svc.cluster.local"
    postgres_port: int = 5432
    postgres_db: str = "agentic"
    postgres_user: str = "postgres"
    postgres_password: str = ""

    # Redis Sentinel
    # SECURITY: Set REDIS_PASSWORD environment variable in production
    redis_host: str = "redis-sentinel.redis-sentinel"
    redis_port: int = 6379
    redis_password: str | None = None

    # Session Management
    session_cache_ttl: int = 3600  # 1 hour
    session_ttl_days: int = 7
    history_ttl_days: int = 30
    context_window_recent: int = 5
    context_window_summary: int = 5

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
