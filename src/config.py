from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "TicketFlow"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database Settings
    POSTGRES_USER: str = "ticketflow_user"
    POSTGRES_PASSWORD: str = "ticketflow_pass"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ticketflow"

    # AI Classifier Settings: "smart_mock" or "openai"
    CLASSIFIER_PROVIDER: str = "smart_mock"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
