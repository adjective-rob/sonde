from pydantic import BaseModel, Field


class ScoringConfig(BaseModel):
    velocity_threshold: float = Field(default=1.0, ge=0)
    relevance_threshold: float = Field(default=0.5, ge=0, le=1)
    novelty_threshold: float = Field(default=0.2, ge=0, le=1)
