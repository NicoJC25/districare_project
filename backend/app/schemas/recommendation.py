from datetime import datetime

from pydantic import BaseModel


class AIRecommendationRead(BaseModel):
    id: str
    emergency_id: str
    recommended_ambulance_id: str | None
    calculated_priority: int
    total_score: float
    decision_reason: str
    candidates_count: int
    criteria: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class CandidateRankingRead(BaseModel):
    recommendation_id: str
    emergency_id: str
    recommended_ambulance_id: str | None
    decision_reason: str
    candidates_count: int
    ranking: list[dict]
