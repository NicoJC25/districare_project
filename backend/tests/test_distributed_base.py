from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.domain.enums import AmbulanceState, AssignmentState, EmergencyState, EventType
from app.models.ambulance import AmbulanceNode
from app.models.assignment import Assignment
from app.models.event import SystemEvent


def create_ambulance(client, code="AMB-A", location="0,0", load=0, reliability=1.0):
    response = client.post(
        "/ambulances",
        json={
            "code": code,
            "simulated_location": location,
            "operational_load": load,
            "reliability": reliability,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_emergency(client, severity=7, location="1,1"):
    response = client.post(
        "/emergencies",
        json={"type": "Accidente", "severity": severity, "simulated_location": location},
    )
    assert response.status_code == 201
    return response.json()


def event_types(db_session):
    return set(db_session.scalars(select(SystemEvent.event_type)).all())


def test_create_emergency_records_events_and_recommendation(client, db_session):
    ambulance = create_ambulance(client, "AMB-A", "0,0")
    emergency = create_emergency(client)

    assert emergency["state"] == EmergencyState.PUBLICADA.value
    recommendations = client.get("/recommendations").json()
    assert recommendations[0]["recommended_ambulance_id"] == ambulance["id"]
    assert EventType.EMERGENCY_CREATED.value in event_types(db_session)
    assert EventType.EMERGENCY_PRIORITIZED.value in event_types(db_session)
    assert EventType.EMERGENCY_PUBLISHED.value in event_types(db_session)


def test_heartbeat_updates_node_and_records_event(client, db_session):
    ambulance = create_ambulance(client)
    response = client.post(f"/ambulances/{ambulance['id']}/heartbeat")

    assert response.status_code == 200
    body = response.json()
    assert body["ambulance"]["last_heartbeat_at"] is not None
    assert EventType.HEARTBEAT_RECEIVED.value in event_types(db_session)


def test_detect_stale_node_marks_failure(client, db_session):
    ambulance = create_ambulance(client)
    node = db_session.get(AmbulanceNode, ambulance["id"])
    node.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=settings.heartbeat_timeout_seconds + 5)
    db_session.commit()

    response = client.post("/failures/detect-stale")

    assert response.status_code == 200
    assert response.json()["detected_failures"] == 1
    db_session.refresh(node)
    assert node.state == AmbulanceState.INACTIVA.value
    assert EventType.NODE_FAILED.value in event_types(db_session)


def test_recover_node_records_event(client, db_session):
    ambulance = create_ambulance(client)
    client.post(f"/ambulances/{ambulance['id']}/fail")

    response = client.post(f"/ambulances/{ambulance['id']}/recover")

    assert response.status_code == 200
    assert response.json()["state"] == AmbulanceState.RECUPERADA.value
    assert EventType.NODE_RECOVERED.value in event_types(db_session)


def test_assignment_unique_constraint_rejects_second_attempt(client, db_session):
    ambulance_a = create_ambulance(client, "AMB-A", "0,0")
    ambulance_b = create_ambulance(client, "AMB-B", "2,2")
    emergency = create_emergency(client)

    first = client.post(
        "/assignments/attempt",
        json={"emergency_id": emergency["id"], "ambulance_id": ambulance_a["id"]},
    ).json()
    second = client.post(
        "/assignments/attempt",
        json={"emergency_id": emergency["id"], "ambulance_id": ambulance_b["id"]},
    ).json()

    assert first["accepted"] is True
    assert second["accepted"] is False
    confirmed = db_session.scalars(
        select(Assignment).where(
            Assignment.emergency_id == emergency["id"],
            Assignment.active.is_(True),
            Assignment.state == AssignmentState.CONFIRMADA.value,
        )
    ).all()
    assert len(confirmed) == 1
    assert EventType.ASSIGNMENT_REJECTED.value in event_types(db_session)


def test_assigned_node_failure_triggers_automatic_reassignment(client, db_session):
    ambulance_a = create_ambulance(client, "AMB-A", "0,0", reliability=1.0)
    ambulance_b = create_ambulance(client, "AMB-B", "1,1", reliability=0.9)
    emergency = create_emergency(client, location="0,0")
    attempt = client.post(
        "/assignments/attempt",
        json={"emergency_id": emergency["id"], "ambulance_id": ambulance_a["id"]},
    ).json()
    assert attempt["accepted"] is True

    response = client.post(f"/ambulances/{ambulance_a['id']}/fail")

    assert response.status_code == 201
    active_assignment = db_session.scalar(
        select(Assignment).where(
            Assignment.emergency_id == emergency["id"],
            Assignment.active.is_(True),
            Assignment.state == AssignmentState.CONFIRMADA.value,
        )
    )
    assert active_assignment is not None
    assert active_assignment.ambulance_id == ambulance_b["id"]
    refreshed_b = db_session.get(AmbulanceNode, ambulance_b["id"])
    assert refreshed_b.state == AmbulanceState.ASIGNADA.value
    assert EventType.REASSIGNMENT_STARTED.value in event_types(db_session)
    assert EventType.REASSIGNMENT_CONFIRMED.value in event_types(db_session)
