from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.domain.enums import AmbulanceState, AssignmentState, EmergencyState, EventType
from app.models.ambulance import AmbulanceNode
from app.models.assignment import Assignment
from app.models.emergency import Emergency
from app.models.event import SystemEvent
from app.messaging.rabbitmq import RabbitMQPublisher
from app.services.location import parse_location, simulated_distance


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


def latest_recommendation(client):
    return client.get("/recommendations").json()[0]


def test_simulated_distance_uses_latitude_longitude_in_kilometers():
    distance = simulated_distance("4.7110,-74.0721", "4.7110,-74.0621")

    assert parse_location("4.7110,-74.0721") == (4.7110, -74.0721)
    assert 1.0 < distance < 1.2
    assert simulated_distance("ubicacion-invalida", "4.7110,-74.0721") == 50.0


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


def test_heuristic_recommendation_prefers_nearest_equivalent_ambulance(client):
    far = create_ambulance(client, "AMB-FAR", "30,0")
    near = create_ambulance(client, "AMB-NEAR", "2,0")

    emergency = create_emergency(client, severity=7, location="0,0")

    recommendation = latest_recommendation(client)
    assert recommendation["recommended_ambulance_id"] == near["id"]
    assert recommendation["decision_reason"].startswith("AMB-NEAR fue recomendada")
    assert recommendation["candidates_count"] == 2
    assert recommendation["criteria"]["selected"]["ambulance_id"] == near["id"]
    assert recommendation["criteria"]["ranking"][0]["ambulance_id"] == near["id"]
    assert recommendation["criteria"]["ranking"][1]["ambulance_id"] == far["id"]

    ranking_response = client.get(f"/emergencies/{emergency['id']}/candidate-ranking")
    assert ranking_response.status_code == 200
    ranking = ranking_response.json()
    assert ranking["recommended_ambulance_id"] == near["id"]
    assert ranking["ranking"][0]["ambulance_id"] == near["id"]
    assert ranking["ranking"][1]["ambulance_id"] == far["id"]


def test_heuristic_recommendation_balances_reliability_and_operational_load(client):
    overloaded = create_ambulance(client, "AMB-OVERLOADED", "0,0", load=10, reliability=0.2)
    balanced = create_ambulance(client, "AMB-BALANCED", "10,0", load=0, reliability=1.0)

    create_emergency(client, severity=7, location="0,0")

    recommendation = latest_recommendation(client)
    assert recommendation["recommended_ambulance_id"] == balanced["id"]
    ranking = recommendation["criteria"]["ranking"]
    overloaded_item = next(item for item in ranking if item["ambulance_id"] == overloaded["id"])
    balanced_item = next(item for item in ranking if item["ambulance_id"] == balanced["id"])
    assert balanced_item["weighted_scores"]["operational_load"] > overloaded_item["weighted_scores"]["operational_load"]
    assert balanced_item["weighted_scores"]["reliability"] > overloaded_item["weighted_scores"]["reliability"]


def test_heuristic_recommendation_penalizes_recovered_availability(client, db_session):
    recovered = create_ambulance(client, "AMB-RECOVERED", "0,0")
    available = create_ambulance(client, "AMB-AVAILABLE", "0,0")
    recovered_node = db_session.get(AmbulanceNode, recovered["id"])
    recovered_node.state = AmbulanceState.RECUPERADA.value
    db_session.commit()

    create_emergency(client, severity=7, location="0,0")

    recommendation = latest_recommendation(client)
    ranking = recommendation["criteria"]["ranking"]
    recovered_item = next(item for item in ranking if item["ambulance_id"] == recovered["id"])
    available_item = next(item for item in ranking if item["ambulance_id"] == available["id"])
    assert recommendation["recommended_ambulance_id"] == available["id"]
    assert available_item["normalized_scores"]["availability"] == 100.0
    assert recovered_item["normalized_scores"]["availability"] == 85.0


def test_heuristic_criteria_exposes_all_required_scores(client):
    create_ambulance(client, "AMB-A", "0,0")

    create_emergency(client, severity=8, location="1,1")

    criteria = latest_recommendation(client)["criteria"]
    expected_criteria = {
        "severity",
        "distance",
        "availability",
        "operational_load",
        "reliability",
        "waiting_time",
    }
    assert set(criteria["weights"]) == expected_criteria
    assert set(criteria["ranking"][0]["normalized_scores"]) == expected_criteria
    assert set(criteria["ranking"][0]["weighted_scores"]) == expected_criteria
    assert criteria["selected"] == criteria["ranking"][0]
    assert criteria["no_candidate_reason"] is None


def test_heuristic_recommendation_records_no_candidate_reason(client):
    create_emergency(client, severity=9, location="1,1")

    recommendation = latest_recommendation(client)
    assert recommendation["recommended_ambulance_id"] is None
    assert recommendation["decision_reason"] == "No hay ambulancias disponibles o recuperadas para recomendar."
    assert recommendation["candidates_count"] == 0
    assert recommendation["criteria"]["ranking"] == []
    assert recommendation["criteria"]["selected"] is None
    assert recommendation["criteria"]["no_candidate_reason"] == (
        "No hay ambulancias disponibles o recuperadas para recomendar."
    )


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
    emergency = create_emergency(client, location="0,0")

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
    assert first["assignment"]["recommendation_id"] is not None
    assert first["assignment"]["recommended_ambulance_id"] == ambulance_a["id"]
    assert first["assignment"]["assignment_reason"] == (
        "La ambulancia asignada coincide con la recomendacion heuristica vigente."
    )
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

    trace = client.get(f"/emergencies/{emergency['id']}/trace").json()
    assert trace["recommended_ambulance_id"] == ambulance_a["id"]
    assert trace["assigned_ambulance_id"] == ambulance_a["id"]
    assert trace["assignment_matches_recommendation"] is True
    assert trace["selected_assignment"]["id"] == first["assignment"]["id"]


def test_emergency_state_update_starts_attention_and_records_event(client, db_session):
    ambulance = create_ambulance(client, "AMB-A", "0,0")
    emergency = create_emergency(client)
    client.post(
        "/assignments/attempt",
        json={"emergency_id": emergency["id"], "ambulance_id": ambulance["id"]},
    )

    response = client.patch(
        f"/emergencies/{emergency['id']}/state",
        json={"state": EmergencyState.EN_ATENCION.value},
    )

    assert response.status_code == 200
    assert response.json()["state"] == EmergencyState.EN_ATENCION.value
    assert db_session.get(AmbulanceNode, ambulance["id"]).state == AmbulanceState.EN_ATENCION.value
    assert EventType.EMERGENCY_STATE_UPDATED.value in event_types(db_session)


def test_emergency_close_finalizes_assignment_and_releases_ambulance(client, db_session):
    ambulance = create_ambulance(client, "AMB-A", "0,0")
    emergency = create_emergency(client)
    attempt = client.post(
        "/assignments/attempt",
        json={"emergency_id": emergency["id"], "ambulance_id": ambulance["id"]},
    ).json()
    client.patch(
        f"/emergencies/{emergency['id']}/state",
        json={"state": EmergencyState.EN_ATENCION.value},
    )

    response = client.patch(
        f"/emergencies/{emergency['id']}/state",
        json={"state": EmergencyState.CERRADA.value},
    )

    assert response.status_code == 200
    assert response.json()["state"] == EmergencyState.CERRADA.value
    assert response.json()["closed_at"] is not None
    assignment = db_session.get(Assignment, attempt["assignment"]["id"])
    assert assignment.active is False
    assert assignment.state == AssignmentState.FINALIZADA.value
    assert assignment.finalized_at is not None
    assert db_session.get(AmbulanceNode, ambulance["id"]).state == AmbulanceState.DISPONIBLE.value
    assert EventType.EMERGENCY_CLOSED.value in event_types(db_session)


def test_closed_emergency_rejects_new_assignment_attempt(client):
    ambulance = create_ambulance(client, "AMB-A", "0,0")
    second_ambulance = create_ambulance(client, "AMB-B", "1,1")
    emergency = create_emergency(client)
    client.post(
        "/assignments/attempt",
        json={"emergency_id": emergency["id"], "ambulance_id": ambulance["id"]},
    )
    client.patch(
        f"/emergencies/{emergency['id']}/state",
        json={"state": EmergencyState.EN_ATENCION.value},
    )
    client.patch(
        f"/emergencies/{emergency['id']}/state",
        json={"state": EmergencyState.CERRADA.value},
    )

    response = client.post(
        "/assignments/attempt",
        json={"emergency_id": emergency["id"], "ambulance_id": second_ambulance["id"]},
    )

    assert response.status_code == 200
    assert response.json() == {"accepted": False, "assignment": None, "reason": "Emergencia no asignable"}


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


def test_trace_records_when_non_recommended_ambulance_wins_distributed_attempt(client):
    far = create_ambulance(client, "AMB-FAR", "30,0")
    near = create_ambulance(client, "AMB-NEAR", "0,0")
    emergency = create_emergency(client, location="0,0")
    recommendation = latest_recommendation(client)
    assert recommendation["recommended_ambulance_id"] == near["id"]

    attempt = client.post(
        "/assignments/attempt",
        json={"emergency_id": emergency["id"], "ambulance_id": far["id"]},
    ).json()

    assert attempt["accepted"] is True
    assert attempt["assignment"]["ambulance_id"] == far["id"]
    assert attempt["assignment"]["recommended_ambulance_id"] == near["id"]
    assert attempt["assignment"]["assignment_reason"] == (
        "La ambulancia asignada no coincide con la recomendacion heuristica vigente; gano por intento distribuido."
    )
    trace = client.get(f"/emergencies/{emergency['id']}/trace").json()
    assert trace["recommended_ambulance_id"] == near["id"]
    assert trace["assigned_ambulance_id"] == far["id"]
    assert trace["assignment_matches_recommendation"] is False
    assert trace["trace_reason"] == attempt["assignment"]["assignment_reason"]


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
    assert active_assignment.recommendation_id is not None
    assert active_assignment.recommended_ambulance_id == ambulance_b["id"]
    assert active_assignment.assignment_reason == (
        "La ambulancia asignada coincide con la recomendacion heuristica vigente."
    )
    assert db_session.get(Emergency, emergency["id"]).assigned_ambulance_id == ambulance_b["id"]
    refreshed_b = db_session.get(AmbulanceNode, ambulance_b["id"])
    assert refreshed_b.state == AmbulanceState.OCUPADO.value
    assert EventType.REASSIGNMENT_STARTED.value in event_types(db_session)
    assert EventType.REASSIGNMENT_CONFIRMED.value in event_types(db_session)

    trace = client.get(f"/emergencies/{emergency['id']}/trace").json()
    assert trace["recommended_ambulance_id"] == ambulance_b["id"]
    assert trace["assigned_ambulance_id"] == ambulance_b["id"]
    assert trace["assignment_matches_recommendation"] is True


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
