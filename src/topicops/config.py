from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_path: Path = Path(".topicops/topicops.db")
    artifact_path: Path = Path(".topicops/artifacts")
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="TOPICOPS_",
        env_file=".env",
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()
