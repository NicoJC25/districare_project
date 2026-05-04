from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import EmergencyState, EventType
from app.messaging.rabbitmq import RabbitMQPublisher
from app.models.emergency import Emergency
from app.schemas.emergency import EmergencyCreate
from app.services.events import EventService
from app.services.recommendations import RecommendationService


class EmergencyService:
    def __init__(self, db: Session):
        self.db = db
        self.events = EventService(db)
        self.publisher = RabbitMQPublisher()

    def create(self, payload: EmergencyCreate) -> Emergency:
        emergency = Emergency(**payload.model_dump(), state=EmergencyState.REGISTRADA.value)
        self.db.add(emergency)
        self.db.flush()
        self.events.record(
            EventType.EMERGENCY_CREATED,
            "Emergencia medica simulada registrada.",
            emergency_id=emergency.id,
        )
        recommendation = RecommendationService(self.db).prioritize(emergency)
        emergency.state = EmergencyState.PUBLICADA.value
        published = self.publisher.publish(
            "emergency.prioritized",
            {
                "event": EventType.EMERGENCY_PUBLISHED.value,
                "emergency_id": emergency.id,
                "recommended_ambulance_id": recommendation.recommended_ambulance_id,
                "priority": emergency.priority,
            },
        )
        self.events.record(
            EventType.EMERGENCY_PUBLISHED,
            "Emergencia priorizada publicada al broker.",
            emergency_id=emergency.id,
            ambulance_id=recommendation.recommended_ambulance_id,
            metadata={"rabbitmq_published": published},
        )
        return emergency

    def list(self) -> list[Emergency]:
        return list(self.db.scalars(select(Emergency).order_by(Emergency.created_at.desc())).all())
