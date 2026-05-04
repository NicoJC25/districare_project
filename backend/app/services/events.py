from sqlalchemy.orm import Session

from app.domain.enums import EventType
from app.models.event import SystemEvent


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        event_type: EventType | str,
        description: str,
        *,
        emergency_id: str | None = None,
        ambulance_id: str | None = None,
        metadata: dict | None = None,
    ) -> SystemEvent:
        event = SystemEvent(
            event_type=str(event_type),
            description=description,
            emergency_id=emergency_id,
            ambulance_id=ambulance_id,
            event_metadata=metadata or {},
        )
        self.db.add(event)
        return event
