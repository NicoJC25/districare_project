from datetime import datetime

from pydantic import BaseModel


class AssignmentAttemptCreate(BaseModel):
    emergency_id: str
    ambulance_id: str


class AssignmentRead(BaseModel):
    id: str
    emergency_id: str
    ambulance_id: str
    recommendation_id: str | None
    recommended_ambulance_id: str | None
    state: str
    active: bool
    assigned_at: datetime
    finalized_at: datetime | None
    reassignment_reason: str | None
    assignment_reason: str | None

    model_config = {"from_attributes": True}


class AssignmentAttemptRead(BaseModel):
    accepted: bool
    assignment: AssignmentRead | None
    reason: str | None = None
