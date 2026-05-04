from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import AmbulanceState, EmergencyState, EventType
from app.models.ambulance import AmbulanceNode
from app.models.emergency import Emergency
from app.models.recommendation import AIRecommendation
from app.services.events import EventService
from app.services.location import simulated_distance


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.events = EventService(db)

    def prioritize(self, emergency: Emergency) -> AIRecommendation:
        candidates = self.db.scalars(
            select(AmbulanceNode).where(AmbulanceNode.state.in_([
                AmbulanceState.DISPONIBLE.value,
                AmbulanceState.RECUPERADA.value,
            ]))
        ).all()

        priority = min(100, emergency.severity * 10)
        ranked = []
        for ambulance in candidates:
            distance = simulated_distance(emergency.simulated_location, ambulance.simulated_location)
            distance_score = max(0.0, 50.0 - distance)
            load_score = max(0.0, 20.0 - float(ambulance.operational_load))
            reliability_score = ambulance.reliability * 30.0
            total = distance_score + load_score + reliability_score + priority
            ranked.append((total, ambulance, distance))

        ranked.sort(key=lambda item: item[0], reverse=True)
        best = ranked[0] if ranked else None
        recommendation = AIRecommendation(
            emergency_id=emergency.id,
            recommended_ambulance_id=best[1].id if best else None,
            calculated_priority=priority,
            total_score=best[0] if best else float(priority),
            criteria={
                "severity": emergency.severity,
                "priority": priority,
                "ranking": [
                    {
                        "ambulance_id": ambulance.id,
                        "code": ambulance.code,
                        "distance": round(distance, 2),
                        "score": round(score, 2),
                    }
                    for score, ambulance, distance in ranked
                ],
            },
        )
        emergency.priority = priority
        emergency.state = EmergencyState.PRIORIZADA.value
        self.db.add(recommendation)
        self.events.record(
            EventType.EMERGENCY_PRIORITIZED,
            "La IA heuristica calculo prioridad y ranking de ambulancias.",
            emergency_id=emergency.id,
            ambulance_id=recommendation.recommended_ambulance_id,
            metadata=recommendation.criteria,
        )
        return recommendation
