from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import AmbulanceState, AssignmentState, EmergencyState, EventType
from app.models.ambulance import AmbulanceNode
from app.models.assignment import Assignment
from app.models.emergency import Emergency
from app.services.events import EventService


class AssignmentService:
    def __init__(self, db: Session):
        self.db = db
        self.events = EventService(db)

    def attempt_assignment(self, emergency_id: str, ambulance_id: str) -> tuple[bool, Assignment | None, str | None]:
        emergency = self.db.get(Emergency, emergency_id)
        ambulance = self.db.get(AmbulanceNode, ambulance_id)
        if emergency is None or ambulance is None:
            return False, None, "Emergencia o ambulancia no encontrada"

        self.events.record(
            EventType.ASSIGNMENT_ATTEMPTED,
            f"{ambulance.code} intenta aceptar emergencia {emergency.id}.",
            emergency_id=emergency.id,
            ambulance_id=ambulance.id,
        )

        if ambulance.state in [AmbulanceState.INACTIVO.value, AmbulanceState.FALLIDO.value]:
            self.events.record(
                EventType.ASSIGNMENT_REJECTED,
                "Intento rechazado: nodo inactivo o fallido.",
                emergency_id=emergency.id,
                ambulance_id=ambulance.id,
            )
            return False, None, "Nodo inactivo o fallido"

        active_assignment = self.db.scalar(
            select(Assignment).where(
                Assignment.emergency_id == emergency.id,
                Assignment.active.is_(True),
                Assignment.state == AssignmentState.CONFIRMADA.value,
            )
        )
        if active_assignment:
            self.events.record(
                EventType.ASSIGNMENT_REJECTED,
                "Intento rechazado: la emergencia ya tiene asignacion activa.",
                emergency_id=emergency.id,
                ambulance_id=ambulance.id,
                metadata={"winner_assignment_id": active_assignment.id},
            )
            return False, None, "Emergencia ya asignada"

        assignment = Assignment(
            emergency_id=emergency.id,
            ambulance_id=ambulance.id,
            state=AssignmentState.CONFIRMADA.value,
            active=True,
        )
        emergency.state = EmergencyState.ASIGNADA.value
        ambulance.state = AmbulanceState.OCUPADO.value
        self.db.add(assignment)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            self.events = EventService(self.db)
            self.events.record(
                EventType.ASSIGNMENT_REJECTED,
                "Intento rechazado por restriccion unica de base de datos.",
                emergency_id=emergency_id,
                ambulance_id=ambulance_id,
            )
            self.db.flush()
            return False, None, "Restriccion unica de asignacion"

        self.events.record(
            EventType.ASSIGNMENT_CONFIRMED,
            f"Asignacion confirmada para {ambulance.code}.",
            emergency_id=emergency.id,
            ambulance_id=ambulance.id,
            metadata={"assignment_id": assignment.id},
        )
        return True, assignment, None

    def deactivate_current_assignment(self, emergency_id: str, reason: str) -> Assignment | None:
        assignment = self.db.scalar(
            select(Assignment).where(
                Assignment.emergency_id == emergency_id,
                Assignment.active.is_(True),
                Assignment.state == AssignmentState.CONFIRMADA.value,
            )
        )
        if assignment is None:
            return None
        assignment.active = False
        assignment.state = AssignmentState.REASIGNADA.value
        assignment.finalized_at = datetime.now(UTC)
        assignment.reassignment_reason = reason
        return assignment
