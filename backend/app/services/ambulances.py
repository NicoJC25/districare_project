from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import AmbulanceState, EventType, FailureRecoveryState
from app.models.ambulance import AmbulanceNode
from app.models.failure import NodeFailure
from app.schemas.ambulance import AmbulanceCreate
from app.schemas.event import NodeEventCreate
from app.services.events import EventService


class AmbulanceService:
    def __init__(self, db: Session):
        self.db = db
        self.events = EventService(db)

    def create(self, payload: AmbulanceCreate) -> AmbulanceNode:
        existing = self.db.scalar(select(AmbulanceNode).where(AmbulanceNode.code == payload.code))
        if existing:
            return existing
        ambulance = AmbulanceNode(**payload.model_dump())
        self.db.add(ambulance)
        self.db.flush()
        self.events.record(
            EventType.AMBULANCE_REGISTERED,
            f"Nodo de ambulancia {ambulance.code} registrado.",
            ambulance_id=ambulance.id,
        )
        return ambulance

    def heartbeat(self, ambulance_id: str) -> tuple[AmbulanceNode, bool]:
        ambulance = self.db.get(AmbulanceNode, ambulance_id)
        if ambulance is None:
            raise ValueError("Ambulancia no encontrada")

        was_inactive = ambulance.state in [AmbulanceState.INACTIVO.value, AmbulanceState.FALLIDO.value]
        ambulance.last_heartbeat_at = datetime.now(UTC)
        ambulance.state = AmbulanceState.DISPONIBLE.value if was_inactive else ambulance.state
        self.events.record(
            EventType.HEARTBEAT_RECEIVED,
            f"Heartbeat recibido desde {ambulance.code}.",
            ambulance_id=ambulance.id,
        )
        if was_inactive:
            self.events.record(
                EventType.NODE_RECOVERED,
                f"Nodo {ambulance.code} recuperado por heartbeat.",
                ambulance_id=ambulance.id,
            )
            failure = self.db.scalar(
                select(NodeFailure)
                .where(
                    NodeFailure.ambulance_id == ambulance.id,
                    NodeFailure.recovery_state == FailureRecoveryState.DETECTADO.value,
                )
                .order_by(NodeFailure.failed_at.desc())
            )
            if failure:
                failure.recovery_state = FailureRecoveryState.RECUPERADO.value
                failure.recovered_at = datetime.now(UTC)
        return ambulance, was_inactive

    def recover(self, ambulance_id: str) -> AmbulanceNode:
        ambulance = self.db.get(AmbulanceNode, ambulance_id)
        if ambulance is None:
            raise ValueError("Ambulancia no encontrada")
        ambulance.state = AmbulanceState.DISPONIBLE.value
        ambulance.last_heartbeat_at = datetime.now(UTC)
        self.events.record(
            EventType.NODE_RECOVERED,
            f"Nodo {ambulance.code} recuperado manualmente.",
            ambulance_id=ambulance.id,
        )
        return ambulance

    def report_node_event(self, ambulance_id: str, payload: NodeEventCreate):
        ambulance = self.db.get(AmbulanceNode, ambulance_id)
        if ambulance is None:
            raise ValueError("Ambulancia no encontrada")

        stage = payload.stage.lower()
        event_type = (
            EventType.NODE_EVENT_RECEIVED
            if stage == "received"
            else EventType.NODE_EVENT_PROCESSED
        )
        description = (
            f"Nodo {ambulance.code} recibio evento de emergencia."
            if event_type == EventType.NODE_EVENT_RECEIVED
            else f"Nodo {ambulance.code} proceso evento de emergencia."
        )
        return self.events.record(
            event_type,
            description,
            emergency_id=payload.emergency_id,
            ambulance_id=ambulance.id,
            metadata={
                "stage": payload.stage,
                "decision": payload.decision,
                "result": payload.result,
                "detail": payload.detail,
                "payload": payload.payload or {},
            },
        )
