from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.enums import AmbulanceState, AssignmentState, EmergencyState, EventType
from app.models.ambulance import AmbulanceNode
from app.models.assignment import Assignment
from app.models.emergency import Emergency
from app.models.failure import NodeFailure
from app.services.assignments import AssignmentService
from app.services.events import EventService
from app.services.recommendations import RecommendationService


class FailureService:
    def __init__(self, db: Session):
        self.db = db
        self.events = EventService(db)

    def detect_stale_nodes(self) -> list[NodeFailure]:
        threshold = datetime.now(UTC) - timedelta(seconds=settings.heartbeat_timeout_seconds)
        nodes = self.db.scalars(
            select(AmbulanceNode).where(
                AmbulanceNode.state != AmbulanceState.INACTIVA.value,
                AmbulanceNode.last_heartbeat_at.is_not(None),
                AmbulanceNode.last_heartbeat_at < threshold,
            )
        ).all()
        return [self.fail_node(node.id, "HEARTBEAT_TIMEOUT", "Timeout de heartbeat") for node in nodes]

    def fail_node(self, ambulance_id: str, failure_type: str = "MANUAL", description: str = "Fallo de nodo") -> NodeFailure:
        ambulance = self.db.get(AmbulanceNode, ambulance_id)
        if ambulance is None:
            raise ValueError("Ambulancia no encontrada")

        ambulance.state = AmbulanceState.INACTIVA.value
        failure = NodeFailure(
            ambulance_id=ambulance.id,
            failure_type=failure_type,
            description=description,
        )
        self.db.add(failure)
        self.events.record(
            EventType.NODE_FAILED,
            f"Nodo {ambulance.code} marcado como inactivo.",
            ambulance_id=ambulance.id,
            metadata={"failure_type": failure_type},
        )

        active_assignment = self.db.scalar(
            select(Assignment).where(
                Assignment.ambulance_id == ambulance.id,
                Assignment.active.is_(True),
                Assignment.state == AssignmentState.CONFIRMADA.value,
            )
        )
        if active_assignment:
            self._reassign_after_failure(active_assignment)
        return failure

    def _reassign_after_failure(self, current_assignment: Assignment) -> None:
        emergency = self.db.get(Emergency, current_assignment.emergency_id)
        if emergency is None:
            return
        AssignmentService(self.db).deactivate_current_assignment(
            emergency.id,
            "Reasignacion por fallo de nodo asignado",
        )
        self.db.flush()
        emergency.state = EmergencyState.REASIGNACION_PENDIENTE.value
        self.events.record(
            EventType.REASSIGNMENT_STARTED,
            "Reasignacion automatica iniciada por fallo del nodo asignado.",
            emergency_id=emergency.id,
            ambulance_id=current_assignment.ambulance_id,
        )

        recommendation = RecommendationService(self.db).prioritize(emergency)
        if recommendation.recommended_ambulance_id:
            accepted, assignment, _ = AssignmentService(self.db).attempt_assignment(
                emergency.id,
                recommendation.recommended_ambulance_id,
            )
            if accepted and assignment:
                emergency.state = EmergencyState.REASIGNADA.value
                self.events.record(
                    EventType.REASSIGNMENT_CONFIRMED,
                    "Reasignacion automatica confirmada.",
                    emergency_id=emergency.id,
                    ambulance_id=assignment.ambulance_id,
                    metadata={"assignment_id": assignment.id},
                )
        else:
            emergency.state = EmergencyState.SIN_UNIDAD_DISPONIBLE.value
