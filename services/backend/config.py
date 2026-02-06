"""Backend settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    public_base_url: str = "https://api-portero.integratec-ia.com"

    # Sitnova default device mapping (override per-tenant later via DB settings)
    hik_user: str = "admin"

    # Biometrics that will validate QR locally
    hik_bio1_host: str = "172.20.22.1"
    hik_bio1_port: int = 80
    hik_bio1_password: str = ""  # .1 uses Integratec20

    hik_bio2_host: str = "172.20.22.136"
    hik_bio2_port: int = 80
    hik_bio2_password: str = ""  # .136 uses integratec20

    hik_timeout_seconds: float = 3.0

    # QR credential parameters (Hikvision CardInfo)
    qr_card_digits: int = 10
    qr_employee_prefix: str = "V"  # employeeNo must be string

    # Timezone for provisioning validity windows to devices (local time expected)
    condo_timezone: str = "America/Costa_Rica"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
