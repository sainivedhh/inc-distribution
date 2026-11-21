"""Central configuration using Pydantic Settings."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Service & Environment
    ENVIRONMENT: str = "test"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    API_TOKEN: Optional[str] = None
    BASE_URL: str = "http://localhost:8000"

    # Simulation Mode
    SIMULATION_MODE: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"

    # Redis / Job Queue
    REDIS_URL: str = "redis://localhost:6379/0"

    # Object Storage (MinIO / S3)
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "incubrix-distribution"
    S3_REGION: str = "us-east-1"

    # Security
    SECRET_ENCRYPTION_KEY: str = "k7R7E-N6yV6s1N3xK1P2l7-v5d_t0A1B2C3D4E5F6G8="  # Fernet 32-byte b64 key for testing
    WEBHOOK_SIGNING_SECRET: str = "test-webhook-secret-32-chars-long-123456"

    # Kill switches per connector (comma separated or specific envs)
    DISABLED_CONNECTORS: str = ""

    # Provider / Adapter
    AI_PROVIDER: str = "mock"
    AI_API_KEY: Optional[str] = None


settings = Settings()
