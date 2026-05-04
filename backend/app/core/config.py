from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DistriCare"
    database_url: str = "postgresql+psycopg://districare:districare@localhost:15432/districare"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5673/"
    rabbitmq_exchange: str = "districare.events"
    heartbeat_timeout_seconds: int = 15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
