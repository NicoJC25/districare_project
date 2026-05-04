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
    created_at: datetime
    closed_at: datetime | None

    model_config = {"from_attributes": True}
