from pydantic import BaseModel


class RegistryStats(BaseModel):
    topic_count: int = 0
    run_count: int = 0
    artifact_count: int = 0
    error_count: int = 0
