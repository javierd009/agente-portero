"""Backend settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    public_base_url: str = "https://api-portero.integratec-ia.com"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
