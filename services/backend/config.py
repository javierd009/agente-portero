"""Backend settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    public_base_url: str = "https://api-portero.integratec-ia.com"

    # Sitnova default device mapping (override per-tenant later via DB settings)
    hik_user: str = "admin"
    hik_pass_default: str = ""  # panel (.3) and biometric (.136)
    hik_pass_pedestrian: str = ""  # pedestrian device (.1)

    hik_panel_host: str = "172.20.22.3"
    hik_panel_port: int = 80

    hik_pedestrian_host: str = "172.20.22.1"
    hik_pedestrian_port: int = 80

    hik_timeout_seconds: float = 3.0

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
