from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DistriCare"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://districare:districare@localhost:15432/districare"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5673/"
    rabbitmq_exchange: str = "districare.events"
    heartbeat_timeout_seconds: int = 15
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    api_key: str = "dev-districare-api-key"
    enable_api_docs: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if not self.is_production:
            return self

        missing = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.rabbitmq_url:
            missing.append("RABBITMQ_URL")
        if not self.backend_cors_origins:
            missing.append("BACKEND_CORS_ORIGINS")
        if not self.api_key or self.api_key == "dev-districare-api-key":
            missing.append("API_KEY")
        if missing:
            raise ValueError(
                "Variables de entorno requeridas para produccion: "
                + ", ".join(missing)
            )
        return self


settings = Settings()
