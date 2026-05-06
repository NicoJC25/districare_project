from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ambulance import AmbulanceNode
from app.models.assignment import Assignment
from app.models.emergency import Emergency
from app.models.event import SystemEvent
from app.models.recommendation import AIRecommendation
from app.schemas.ambulance import AmbulanceCreate, AmbulanceRead, HeartbeatRead
from app.schemas.assignment import AssignmentAttemptCreate, AssignmentAttemptRead, AssignmentRead
from app.schemas.emergency import EmergencyCreate, EmergencyRead
from app.schemas.event import NodeEventCreate, SystemEventRead
from app.schemas.recommendation import AIRecommendationRead
from app.services.ambulances import AmbulanceService
from app.services.assignments import AssignmentService
from app.services.emergencies import EmergencyService
from app.services.failures import FailureService

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Base de datos no disponible: {exc.__class__.__name__}",
        ) from exc
    return {"status": "ok", "service": "districare", "database": "ok"}


@router.post("/emergencies", response_model=EmergencyRead, status_code=201)
def create_emergency(payload: EmergencyCreate, db: Session = Depends(get_db)) -> Emergency:
    emergency = EmergencyService(db).create(payload)
    db.commit()
    db.refresh(emergency)
    return emergency


@router.get("/emergencies", response_model=list[EmergencyRead])
def list_emergencies(db: Session = Depends(get_db)) -> list[Emergency]:
    return EmergencyService(db).list()


@router.get("/emergencies/{emergency_id}", response_model=EmergencyRead)
def get_emergency(emergency_id: str, db: Session = Depends(get_db)) -> Emergency:
    emergency = db.get(Emergency, emergency_id)
    if emergency is None:
        raise HTTPException(status_code=404, detail="Emergencia no encontrada")
    return emergency


@router.post("/ambulances", response_model=AmbulanceRead, status_code=201)
def create_ambulance(payload: AmbulanceCreate, db: Session = Depends(get_db)) -> AmbulanceNode:
    ambulance = AmbulanceService(db).create(payload)
    db.commit()
    db.refresh(ambulance)
    return ambulance


@router.get("/ambulances", response_model=list[AmbulanceRead])
def list_ambulances(db: Session = Depends(get_db)) -> list[AmbulanceNode]:
    return list(db.scalars(select(AmbulanceNode).order_by(AmbulanceNode.code)).all())


@router.post("/ambulances/{ambulance_id}/heartbeat", response_model=HeartbeatRead)
def heartbeat(ambulance_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        ambulance, recovered = AmbulanceService(db).heartbeat(ambulance_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(ambulance)
    return {"ambulance": ambulance, "recovered": recovered}


@router.post("/ambulances/{ambulance_id}/fail", status_code=201)
def fail_ambulance(ambulance_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        failure = FailureService(db).fail_node(ambulance_id, "MANUAL", "Fallo manual desde API")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return {"failure_id": failure.id}


@router.post("/ambulances/{ambulance_id}/recover", response_model=AmbulanceRead)
def recover_ambulance(ambulance_id: str, db: Session = Depends(get_db)) -> AmbulanceNode:
    try:
        ambulance = AmbulanceService(db).recover(ambulance_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(ambulance)
    return ambulance


@router.post("/ambulances/{ambulance_id}/node-events", response_model=SystemEventRead, status_code=201)
def report_node_event(
    ambulance_id: str,
    payload: NodeEventCreate,
    db: Session = Depends(get_db),
) -> SystemEvent:
    try:
        event = AmbulanceService(db).report_node_event(ambulance_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(event)
    return event


@router.post("/assignments/attempt", response_model=AssignmentAttemptRead)
def attempt_assignment(payload: AssignmentAttemptCreate, db: Session = Depends(get_db)) -> dict:
    accepted, assignment, reason = AssignmentService(db).attempt_assignment(
        payload.emergency_id,
        payload.ambulance_id,
    )
    db.commit()
    return {"accepted": accepted, "assignment": assignment, "reason": reason}


@router.get("/assignments", response_model=list[AssignmentRead])
def list_assignments(db: Session = Depends(get_db)) -> list[Assignment]:
    return list(db.scalars(select(Assignment).order_by(Assignment.assigned_at.desc())).all())


@router.post("/failures/detect-stale")
def detect_stale_nodes(db: Session = Depends(get_db)) -> dict:
    failures = FailureService(db).detect_stale_nodes()
    db.commit()
    return {"detected_failures": len(failures), "failure_ids": [failure.id for failure in failures]}


@router.get("/events", response_model=list[SystemEventRead])
def list_events(db: Session = Depends(get_db)) -> list[SystemEvent]:
    return list(db.scalars(select(SystemEvent).order_by(SystemEvent.created_at.desc())).all())


@router.get("/recommendations", response_model=list[AIRecommendationRead])
def list_recommendations(db: Session = Depends(get_db)) -> list[AIRecommendation]:
    return list(db.scalars(select(AIRecommendation).order_by(AIRecommendation.created_at.desc())).all())
