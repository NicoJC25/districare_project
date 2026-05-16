from datetime import datetime

from pydantic import BaseModel, Field


class EmergencyCreate(BaseModel):
    type: str
    severity: int = Field(ge=1, le=10)
    simulated_location: str


class EmergencyRead(BaseModel):
    id: str
    type: str
    severity: int
    priority: int | None
    simulated_location: str
    state: str
    assigned_ambulance_id: str | None
    created_at: datetime
    closed_at: datetime | None

    model_config = {"from_attributes": True}


class EmergencyTraceRead(BaseModel):
    emergency: EmergencyRead
    latest_recommendation: dict | None
    selected_assignment: dict | None
    recommended_ambulance_id: str | None
    assigned_ambulance_id: str | None
    assignment_matches_recommendation: bool | None
    trace_reason: str
    events: list[dict]
