from datetime import datetime

from pydantic import BaseModel


class SystemEventRead(BaseModel):
    id: str
    emergency_id: str | None
    ambulance_id: str | None
    event_type: str
    description: str
    event_metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}
