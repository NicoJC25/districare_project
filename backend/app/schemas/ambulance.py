from datetime import datetime

from pydantic import BaseModel, Field


class AmbulanceCreate(BaseModel):
    code: str
    simulated_location: str
    operational_load: int = Field(default=0, ge=0)
    reliability: float = Field(default=1.0, ge=0, le=1)


class AmbulanceRead(BaseModel):
    id: str
    code: str
    state: str
    simulated_location: str
    operational_load: int
    reliability: float
    last_heartbeat_at: datetime | None

    model_config = {"from_attributes": True}


class HeartbeatRead(BaseModel):
    ambulance: AmbulanceRead
    recovered: bool = False
