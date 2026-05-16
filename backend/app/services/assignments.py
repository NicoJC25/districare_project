from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import AmbulanceState, AssignmentState, EmergencyState, EventType
from app.models.ambulance import AmbulanceNode
from app.models.assignment import Assignment
from app.models.emergency import Emergency
from app.models.recommendation import AIRecommendation
from app.services.events import EventService


class AssignmentService:
    ASSIGNABLE_EMERGENCY_STATES = {
        EmergencyState.PRIORIZADA.value,
        EmergencyState.PUBLICADA.value,
        EmergencyState.EN_PROCESO_ASIGNACION.value,
        EmergencyState.REASIGNACION_PENDIENTE.value,
    }
    ASSIGNABLE_AMBULANCE_STATES = {
        AmbulanceState.DISPONIBLE.value,
        AmbulanceState.RECUPERADA.value,
        AmbulanceState.CANDIDATA.value,
        AmbulanceState.INTENTANDO_ACEPTAR.value,
    }

    def __init__(self, db: Session):
        self.db = db
        self.events = EventService(db)

    def attempt_assignment(self, emergency_id: str, ambulance_id: str) -> tuple[bool, Assignment | None, str | None]:
        emergency = self.db.scalar(
            select(Emergency)
            .where(Emergency.id == emergency_id)
            .with_for_update()
        )
        ambulance = self.db.scalar(
            select(AmbulanceNode)
            .where(AmbulanceNode.id == ambulance_id)
            .with_for_update()
        )
        if emergency is None or ambulance is None:
            return False, None, "Emergencia o ambulancia no encontrada"

        self.events.record(
            EventType.ASSIGNMENT_ATTEMPTED,
            f"{ambulance.code} intenta aceptar emergencia {emergency.id}.",
            emergency_id=emergency.id,
            ambulance_id=ambulance.id,
        )

        active_assignment = self._active_assignment_for_emergency(emergency.id)
        if active_assignment:
            if active_assignment.ambulance_id == ambulance.id:
                return True, active_assignment, None
            self.events.record(
                EventType.ASSIGNMENT_REJECTED,
                "Intento rechazado: la emergencia ya tiene asignacion activa.",
                emergency_id=emergency.id,
                ambulance_id=ambulance.id,
                metadata={"winner_assignment_id": active_assignment.id},
            )
            return False, None, "Emergencia ya asignada"

        if emergency.state not in self.ASSIGNABLE_EMERGENCY_STATES:
            self.events.record(
                EventType.ASSIGNMENT_REJECTED,
                "Intento rechazado: la emergencia no esta en estado asignable.",
                emergency_id=emergency.id,
                ambulance_id=ambulance.id,
                metadata={"emergency_state": emergency.state},
            )
            return False, None, "Emergencia no asignable"

        ambulance_assignment = self._active_assignment_for_ambulance(ambulance.id)
        if ambulance_assignment:
            self.events.record(
                EventType.ASSIGNMENT_REJECTED,
                "Intento rechazado: el nodo ya tiene asignacion activa.",
                emergency_id=emergency.id,
                ambulance_id=ambulance.id,
                metadata={"active_assignment_id": ambulance_assignment.id},
            )
            return False, None, "Nodo ya asignado"

        if ambulance.state not in self.ASSIGNABLE_AMBULANCE_STATES:
            self.events.record(
                EventType.ASSIGNMENT_REJECTED,
                "Intento rechazado: nodo no disponible para asignacion.",
                emergency_id=emergency.id,
                ambulance_id=ambulance.id,
                metadata={"ambulance_state": ambulance.state},
            )
            return False, None, "Nodo no disponible"

        recommendation = self._latest_recommendation_for_emergency(emergency.id)
        assignment = Assignment(
            emergency_id=emergency.id,
            ambulance_id=ambulance.id,
            recommendation_id=recommendation.id if recommendation else None,
            recommended_ambulance_id=recommendation.recommended_ambulance_id if recommendation else None,
            state=AssignmentState.CONFIRMADA.value,
            active=True,
            assignment_reason=self._assignment_reason(ambulance, recommendation),
        )
        emergency.state = EmergencyState.EN_PROCESO_ASIGNACION.value
        self.db.add(assignment)
        try:
            self.db.flush()
        except IntegrityError:
            return self._reject_unique_assignment_conflict(emergency_id, ambulance_id)

        emergency.state = EmergencyState.ASIGNADA.value
        emergency.assigned_ambulance_id = ambulance.id
        ambulance.state = AmbulanceState.OCUPADO.value
        self.db.flush()

        self.events.record(
            EventType.ASSIGNMENT_CONFIRMED,
            f"Asignacion confirmada para {ambulance.code}.",
            emergency_id=emergency.id,
            ambulance_id=ambulance.id,
            metadata={
                "assignment_id": assignment.id,
                "recommendation_id": assignment.recommendation_id,
                "recommended_ambulance_id": assignment.recommended_ambulance_id,
                "assigned_ambulance_id": assignment.ambulance_id,
                "assignment_reason": assignment.assignment_reason,
            },
        )
        return True, assignment, None

    def deactivate_current_assignment(self, emergency_id: str, reason: str) -> Assignment | None:
        assignment = self._active_assignment_for_emergency(emergency_id)
        if assignment is None:
            return None
        assignment.active = False
        assignment.state = AssignmentState.REASIGNADA.value
        assignment.finalized_at = datetime.now(UTC)
        assignment.reassignment_reason = reason
        emergency = self.db.get(Emergency, emergency_id)
        if emergency:
            emergency.assigned_ambulance_id = None
        return assignment

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

    def _active_assignment_for_ambulance(self, ambulance_id: str) -> Assignment | None:
        return self.db.scalar(
            select(Assignment)
            .where(
                Assignment.ambulance_id == ambulance_id,
                Assignment.active.is_(True),
                Assignment.state == AssignmentState.CONFIRMADA.value,
            )
            .with_for_update()
        )

    def _latest_recommendation_for_emergency(self, emergency_id: str) -> AIRecommendation | None:
        return self.db.scalar(
            select(AIRecommendation)
            .where(AIRecommendation.emergency_id == emergency_id)
            .order_by(AIRecommendation.created_at.desc(), AIRecommendation.id.desc())
        )

    def _assignment_reason(
        self,
        ambulance: AmbulanceNode,
        recommendation: AIRecommendation | None,
    ) -> str:
        if recommendation is None:
            return "Asignacion confirmada sin recomendacion previa registrada."
        if recommendation.recommended_ambulance_id is None:
            return "Asignacion confirmada aunque la recomendacion no tenia candidata disponible."
        if recommendation.recommended_ambulance_id == ambulance.id:
            return "La ambulancia asignada coincide con la recomendacion heuristica vigente."
        return "La ambulancia asignada no coincide con la recomendacion heuristica vigente; gano por intento distribuido."

    def _reject_unique_assignment_conflict(
        self,
        emergency_id: str,
        ambulance_id: str,
    ) -> tuple[bool, None, str]:
        self.db.rollback()
        self.events = EventService(self.db)
        emergency_winner = self._active_assignment_for_emergency(emergency_id)
        ambulance_winner = self._active_assignment_for_ambulance(ambulance_id)
        reason = "Emergencia ya asignada" if emergency_winner else "Nodo ya asignado"
        self.events.record(
            EventType.ASSIGNMENT_REJECTED,
            "Intento rechazado por validacion atomica de asignacion exclusiva.",
            emergency_id=emergency_id,
            ambulance_id=ambulance_id,
            metadata={
                "emergency_winner_assignment_id": emergency_winner.id if emergency_winner else None,
                "ambulance_winner_assignment_id": ambulance_winner.id if ambulance_winner else None,
            },
        )
        self.db.flush()
        return False, None, reason
