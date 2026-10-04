import os
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "development"
    database_url: str = "sqlite:///./hupiao.db"
    redis_url: str = ""
    token_pepper: str = "local-development-only-change-before-deployment"
    admin_token: str = ""
    support_email: str = ""
    public_api_url: str = Field(
        default_factory=lambda: os.environ.get(
            "RENDER_EXTERNAL_URL", "http://127.0.0.1:8000"
        )
    )
    cors_origins: list[str] = []
    pool_size: int = 5
    max_overflow: int = 5
    moderate_before_publish: bool = True

    @field_validator("database_url", mode="before")
    @classmethod
    def postgres_driver(cls, value):
        # Managed providers return a plain PostgreSQL URL; this project uses psycopg 3.
        if isinstance(value, str):
            for prefix in ("postgres://", "postgresql://"):
                if value.startswith(prefix):
                    return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    def validate_production(self):
        if self.environment == "production":
            if not self.database_url.startswith("postgresql+"):
                raise RuntimeError("Production requires PostgreSQL")
            if not self.redis_url:
                raise RuntimeError("Production requires shared Redis rate limiting")
            if len(self.token_pepper) < 32 or self.token_pepper.startswith("local-"):
                raise RuntimeError("Set a private TOKEN_PEPPER")
            if len(self.admin_token) < 32:
                raise RuntimeError("Set a private ADMIN_TOKEN")
            if not self.public_api_url.startswith("https://"):
                raise RuntimeError("Production API requires HTTPS")
            if "@" not in self.support_email or "example" in self.support_email:
                raise RuntimeError("Set a real SUPPORT_EMAIL")
            if not self.moderate_before_publish:
                raise RuntimeError("Production requires pre-publication moderation")


settings = Settings()
settings.validate_production()
