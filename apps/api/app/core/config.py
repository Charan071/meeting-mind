from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://meetingmind:meetingmind@localhost:5432/meetingmind"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    NEXTAUTH_SECRET: str = "change-me-in-production"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # AI — cloud (optional, falls back to Ollama if blank)
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Ollama — local fallback
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "llama3.1:8b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # Recall.ai
    RECALL_API_KEY: str = ""
    RECALL_WEBHOOK_SECRET: str = ""
    RECALL_BASE_URL: str = "https://api.recall.ai/api/v1"

    # Composio
    COMPOSIO_API_KEY: str = ""

    # Storage
    S3_BUCKET: str = "meetingmind-transcripts"
    S3_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Sentry
    SENTRY_DSN: str = ""

    # App URL (for webhooks)
    API_BASE_URL: str = "http://localhost:8000"


settings = Settings()
