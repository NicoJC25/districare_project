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
from app.schemas.emergency import EmergencyCreate, EmergencyRead, EmergencyStateUpdate, EmergencyTraceRead
from app.schemas.event import NodeEventCreate, SystemEventRead
from app.schemas.recommendation import AIRecommendationRead, CandidateRankingRead
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


@router.patch("/emergencies/{emergency_id}/state", response_model=EmergencyRead)
def update_emergency_state(
    emergency_id: str,
    payload: EmergencyStateUpdate,
    db: Session = Depends(get_db),
) -> Emergency:
    try:
        emergency = EmergencyService(db).update_state(emergency_id, payload.state)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(emergency)
    return emergency


@router.get("/emergencies/{emergency_id}/candidate-ranking", response_model=CandidateRankingRead)
def get_candidate_ranking(emergency_id: str, db: Session = Depends(get_db)) -> dict:
    emergency = db.get(Emergency, emergency_id)
    if emergency is None:
        raise HTTPException(status_code=404, detail="Emergencia no encontrada")
    recommendation = _latest_recommendation(db, emergency_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recomendacion no encontrada")
    return {
        "recommendation_id": recommendation.id,
        "emergency_id": emergency_id,
        "recommended_ambulance_id": recommendation.recommended_ambulance_id,
        "decision_reason": recommendation.decision_reason,
        "candidates_count": recommendation.candidates_count,
        "ranking": recommendation.criteria.get("ranking", []),
    }


@router.get("/emergencies/{emergency_id}/trace", response_model=EmergencyTraceRead)
def get_emergency_trace(emergency_id: str, db: Session = Depends(get_db)) -> dict:
    emergency = db.get(Emergency, emergency_id)
    if emergency is None:
        raise HTTPException(status_code=404, detail="Emergencia no encontrada")
    recommendation = _latest_recommendation(db, emergency_id)
    assignment = _trace_assignment(db, emergency_id)
    events = list(
        db.scalars(
            select(SystemEvent)
            .where(SystemEvent.emergency_id == emergency_id)
            .order_by(SystemEvent.created_at.asc())
        ).all()
    )
    recommended_ambulance_id = recommendation.recommended_ambulance_id if recommendation else None
    assigned_ambulance_id = assignment.ambulance_id if assignment else emergency.assigned_ambulance_id
    matches = (
        None
        if recommended_ambulance_id is None or assigned_ambulance_id is None
        else recommended_ambulance_id == assigned_ambulance_id
    )
    return {
        "emergency": EmergencyRead.model_validate(emergency).model_dump(),
        "latest_recommendation": (
            AIRecommendationRead.model_validate(recommendation).model_dump()
            if recommendation
            else None
        ),
        "selected_assignment": (
            AssignmentRead.model_validate(assignment).model_dump()
            if assignment
            else None
        ),
        "recommended_ambulance_id": recommended_ambulance_id,
        "assigned_ambulance_id": assigned_ambulance_id,
        "assignment_matches_recommendation": matches,
        "trace_reason": _trace_reason(recommendation, assignment),
        "events": [SystemEventRead.model_validate(event).model_dump() for event in events],
    }


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


def _latest_recommendation(db: Session, emergency_id: str) -> AIRecommendation | None:
    return db.scalar(
        select(AIRecommendation)
        .where(AIRecommendation.emergency_id == emergency_id)
        .order_by(AIRecommendation.created_at.desc(), AIRecommendation.id.desc())
    )


def _trace_assignment(db: Session, emergency_id: str) -> Assignment | None:
    active = db.scalar(
        select(Assignment)
        .where(
            Assignment.emergency_id == emergency_id,
            Assignment.active.is_(True),
        )
        .order_by(Assignment.assigned_at.desc(), Assignment.id.desc())
    )
    if active:
        return active
    return db.scalar(
        select(Assignment)
        .where(Assignment.emergency_id == emergency_id)
        .order_by(Assignment.assigned_at.desc(), Assignment.id.desc())
    )


def _trace_reason(
    recommendation: AIRecommendation | None,
    assignment: Assignment | None,
) -> str:
    if recommendation is None:
        return "La emergencia no tiene recomendacion registrada."
    if assignment is None:
        return recommendation.decision_reason
    return assignment.assignment_reason or recommendation.decision_reason
