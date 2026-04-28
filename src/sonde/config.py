from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_path: Path = Path(".sonde/sonde.db")
    artifact_path: Path = Path(".sonde/artifacts")
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="SONDE_",
        env_file=".env",
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()
