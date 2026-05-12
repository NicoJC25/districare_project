from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.domain.enums import AmbulanceState, AssignmentState, EmergencyState, EventType
from app.models.ambulance import AmbulanceNode
from app.models.assignment import Assignment
from app.models.emergency import Emergency
from app.models.event import SystemEvent
from app.messaging.rabbitmq import RabbitMQPublisher


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


def test_create_emergency_records_events_recommendation_and_publishes_payload(client, db_session, monkeypatch):
    published = {}
    monkeypatch.setattr(
        RabbitMQPublisher,
        "publish",
        lambda self, routing_key, payload: published.update({"routing_key": routing_key, "payload": payload}) or True,
    )
    ambulance = create_ambulance(client, "AMB-A", "0,0")
    emergency = create_emergency(client)

    assert emergency["state"] == EmergencyState.PUBLICADA.value
    recommendations = client.get("/recommendations").json()
    assert recommendations[0]["recommended_ambulance_id"] == ambulance["id"]
    assert EventType.EMERGENCY_CREATED.value in event_types(db_session)
    assert EventType.EMERGENCY_PRIORITIZED.value in event_types(db_session)
    assert EventType.EMERGENCY_PUBLISHED.value in event_types(db_session)
    assert published["routing_key"] == "emergency.prioritized"
    assert published["payload"] == {
        "event": EventType.EMERGENCY_PUBLISHED.value,
        "emergency_id": emergency["id"],
        "type": emergency["type"],
        "severity": emergency["severity"],
        "simulated_location": emergency["simulated_location"],
        "recommended_ambulance_id": ambulance["id"],
        "priority": emergency["priority"],
    }


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
    assert node.state == AmbulanceState.FALLIDO.value
    assert EventType.NODE_FAILED.value in event_types(db_session)


def test_recover_node_records_event(client, db_session):
    ambulance = create_ambulance(client)
    client.post(f"/ambulances/{ambulance['id']}/fail")

    response = client.post(f"/ambulances/{ambulance['id']}/recover")

    assert response.status_code == 200
    assert response.json()["state"] == AmbulanceState.DISPONIBLE.value
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
    assert first["assignment"]["ambulance_id"] == ambulance_a["id"]
    emergency_row = db_session.get(Emergency, emergency["id"])
    assert emergency_row.state == EmergencyState.ASIGNADA.value
    assert emergency_row.assigned_ambulance_id == ambulance_a["id"]
    db_session.refresh(db_session.get(AmbulanceNode, ambulance_a["id"]))
    assert db_session.get(AmbulanceNode, ambulance_a["id"]).state == AmbulanceState.OCUPADO.value
    confirmed = db_session.scalars(
        select(Assignment).where(
            Assignment.emergency_id == emergency["id"],
            Assignment.active.is_(True),
            Assignment.state == AssignmentState.CONFIRMADA.value,
        )
    ).all()
    assert len(confirmed) == 1
    assert EventType.ASSIGNMENT_REJECTED.value in event_types(db_session)


def test_assignment_rejects_ambulance_with_active_assignment(client, db_session):
    ambulance = create_ambulance(client, "AMB-A", "0,0")
    emergency_a = create_emergency(client, location="0,0")
    emergency_b = create_emergency(client, location="2,2")

    first = client.post(
        "/assignments/attempt",
        json={"emergency_id": emergency_a["id"], "ambulance_id": ambulance["id"]},
    ).json()
    second = client.post(
        "/assignments/attempt",
        json={"emergency_id": emergency_b["id"], "ambulance_id": ambulance["id"]},
    ).json()

    assert first["accepted"] is True
    assert second == {"accepted": False, "assignment": None, "reason": "Nodo ya asignado"}
    assert db_session.get(Emergency, emergency_b["id"]).assigned_ambulance_id is None
    confirmed = db_session.scalars(
        select(Assignment).where(
            Assignment.ambulance_id == ambulance["id"],
            Assignment.active.is_(True),
            Assignment.state == AssignmentState.CONFIRMADA.value,
        )
    ).all()
    assert len(confirmed) == 1


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
    assert db_session.get(Emergency, emergency["id"]).assigned_ambulance_id == ambulance_b["id"]
    refreshed_b = db_session.get(AmbulanceNode, ambulance_b["id"])
    assert refreshed_b.state == AmbulanceState.OCUPADO.value
    assert EventType.REASSIGNMENT_STARTED.value in event_types(db_session)
    assert EventType.REASSIGNMENT_CONFIRMED.value in event_types(db_session)


def test_node_event_endpoint_records_received_and_processed_events(client, db_session):
    ambulance = create_ambulance(client)
    emergency = create_emergency(client)

    received = client.post(
        f"/ambulances/{ambulance['id']}/node-events",
        json={
            "stage": "received",
            "emergency_id": emergency["id"],
            "decision": "received",
            "result": "received",
            "payload": {"emergency_id": emergency["id"]},
        },
    )
    processed = client.post(
        f"/ambulances/{ambulance['id']}/node-events",
        json={
            "stage": "processed",
            "emergency_id": emergency["id"],
            "decision": "ignored",
            "result": "not_recommended",
            "detail": "La emergencia no fue recomendada para este nodo.",
            "payload": {"emergency_id": emergency["id"]},
        },
    )

    assert received.status_code == 201
    assert received.json()["event_type"] == EventType.NODE_EVENT_RECEIVED.value
    assert processed.status_code == 201
    assert processed.json()["event_type"] == EventType.NODE_EVENT_PROCESSED.value
    assert EventType.NODE_EVENT_RECEIVED.value in event_types(db_session)
    assert EventType.NODE_EVENT_PROCESSED.value in event_types(db_session)


def test_events_endpoint_exposes_published_received_and_processed_events(client):
    ambulance = create_ambulance(client)
    emergency = create_emergency(client)
    client.post(
        f"/ambulances/{ambulance['id']}/node-events",
        json={"stage": "received", "emergency_id": emergency["id"], "decision": "received"},
    )
    client.post(
        f"/ambulances/{ambulance['id']}/node-events",
        json={"stage": "processed", "emergency_id": emergency["id"], "decision": "attempted", "result": "accepted"},
    )

    events = client.get("/events").json()
    exposed_types = {event["event_type"] for event in events}

    assert EventType.EMERGENCY_PUBLISHED.value in exposed_types
    assert EventType.NODE_EVENT_RECEIVED.value in exposed_types
    assert EventType.NODE_EVENT_PROCESSED.value in exposed_types


def test_assignments_endpoint_lists_confirmed_assignments(client):
    ambulance = create_ambulance(client)
    emergency = create_emergency(client)
    client.post(
        "/assignments/attempt",
        json={"emergency_id": emergency["id"], "ambulance_id": ambulance["id"]},
    )

    assignments = client.get("/assignments").json()

    assert len(assignments) == 1
    assert assignments[0]["emergency_id"] == emergency["id"]
    assert assignments[0]["ambulance_id"] == ambulance["id"]
