from datetime import datetime

from pydantic import BaseModel


class AIRecommendationRead(BaseModel):
    id: str
    emergency_id: str
    recommended_ambulance_id: str | None
    calculated_priority: int
    total_score: float
    criteria: dict
    created_at: datetime

    model_config = {"from_attributes": True}
