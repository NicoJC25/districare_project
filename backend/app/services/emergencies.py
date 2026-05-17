from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import AmbulanceState, AssignmentState, EmergencyState, EventType
from app.models.assignment import Assignment
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
                "type": emergency.type,
                "severity": emergency.severity,
                "simulated_location": emergency.simulated_location,
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

    def update_state(self, emergency_id: str, target_state: str) -> Emergency:
        if target_state not in {EmergencyState.EN_ATENCION.value, EmergencyState.CERRADA.value}:
            raise ValueError("Estado no permitido para actualizacion manual")

        emergency = self.db.scalar(
            select(Emergency)
            .where(Emergency.id == emergency_id)
            .with_for_update()
        )
        if emergency is None:
            raise LookupError("Emergencia no encontrada")
        if emergency.state == EmergencyState.CERRADA.value:
            raise ValueError("La emergencia ya esta cerrada")

        active_assignment = self._active_assignment_for_emergency(emergency.id)
        if target_state == EmergencyState.EN_ATENCION.value:
            return self._start_attention(emergency, active_assignment)
        return self._close(emergency, active_assignment)

    def _start_attention(self, emergency: Emergency, assignment: Assignment | None) -> Emergency:
        if emergency.state not in {EmergencyState.PUBLICADA.value, EmergencyState.ASIGNADA.value}:
            raise ValueError("La emergencia no esta en un estado valido para iniciar atencion")
        if assignment is None:
            raise ValueError("No se puede iniciar atencion sin asignacion activa")

        previous_state = emergency.state
        emergency.state = EmergencyState.EN_ATENCION.value
        if assignment.ambulance:
            assignment.ambulance.state = AmbulanceState.EN_ATENCION.value
        self.events.record(
            EventType.EMERGENCY_STATE_UPDATED,
            "Emergencia paso a estado EN_ATENCION.",
            emergency_id=emergency.id,
            ambulance_id=assignment.ambulance_id,
            metadata={"previous_state": previous_state, "new_state": emergency.state},
        )
        return emergency

    def _close(self, emergency: Emergency, assignment: Assignment | None) -> Emergency:
        if emergency.state not in {EmergencyState.EN_ATENCION.value, EmergencyState.SIN_UNIDAD_DISPONIBLE.value}:
            raise ValueError("La emergencia no esta en un estado valido para cierre")
        if assignment is None and emergency.state != EmergencyState.SIN_UNIDAD_DISPONIBLE.value:
            raise ValueError("No se puede cerrar una emergencia sin asignacion activa")

        previous_state = emergency.state
        emergency.state = EmergencyState.CERRADA.value
        emergency.closed_at = datetime.now(UTC)
        if assignment is not None:
            assignment.active = False
            assignment.state = AssignmentState.FINALIZADA.value
            assignment.finalized_at = emergency.closed_at
            if assignment.ambulance:
                assignment.ambulance.state = AmbulanceState.DISPONIBLE.value

        self.events.record(
            EventType.EMERGENCY_CLOSED,
            "Emergencia cerrada y ciclo de atencion finalizado.",
            emergency_id=emergency.id,
            ambulance_id=assignment.ambulance_id if assignment else None,
            metadata={
                "previous_state": previous_state,
                "new_state": emergency.state,
                "assignment_id": assignment.id if assignment else None,
            },
        )
        return emergency

    def _active_assignment_for_emergency(self, emergency_id: str) -> Assignment | None:
        return self.db.scalar(
            select(Assignment)
            .where(
                Assignment.emergency_id == emergency_id,
                Assignment.active.is_(True),
                Assignment.state == AssignmentState.CONFIRMADA.value,
            )
            .with_for_update()
        )
