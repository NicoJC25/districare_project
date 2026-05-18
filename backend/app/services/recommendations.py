from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import AmbulanceState, EmergencyState, EventType
from app.models.ambulance import AmbulanceNode
from app.models.emergency import Emergency
from app.models.recommendation import AIRecommendation
from app.services.events import EventService
from app.services.location import simulated_distance


class RecommendationService:
    WEIGHTS = {
        "severity": 0.25,
        "distance": 0.25,
        "availability": 0.15,
        "operational_load": 0.15,
        "reliability": 0.15,
        "waiting_time": 0.05,
    }
    MAX_DISTANCE = 20.0
    MAX_OPERATIONAL_LOAD = 10.0
    MAX_WAITING_SECONDS = 30 * 60
    AVAILABILITY_SCORES = {
        AmbulanceState.DISPONIBLE.value: 100.0,
        AmbulanceState.RECUPERADA.value: 85.0,
    }

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

        priority = self._severity_score(emergency)
        waiting_score = self._waiting_time_score(emergency)
        ranked = []
        for ambulance in candidates:
            distance = simulated_distance(emergency.simulated_location, ambulance.simulated_location)
            scores = {
                "severity": priority,
                "distance": self._distance_score(distance),
                "availability": self._availability_score(ambulance),
                "operational_load": self._operational_load_score(ambulance),
                "reliability": self._reliability_score(ambulance),
                "waiting_time": waiting_score,
            }
            weighted_scores = {
                criterion: scores[criterion] * weight
                for criterion, weight in self.WEIGHTS.items()
            }
            total = sum(weighted_scores.values())
            ranked.append(
                {
                    "total_score": total,
                    "ambulance": ambulance,
                    "distance": distance,
                    "scores": scores,
                    "weighted_scores": weighted_scores,
                }
            )

        ranked.sort(
            key=lambda item: (
                item["total_score"],
                -item["distance"],
                item["ambulance"].reliability,
            ),
            reverse=True,
        )
        best = ranked[0] if ranked else None
        criteria = self._build_criteria(emergency, priority, waiting_score, ranked, best)
        decision_reason = self._decision_reason(best)
        recommendation = AIRecommendation(
            emergency_id=emergency.id,
            recommended_ambulance_id=best["ambulance"].id if best else None,
            calculated_priority=priority,
            total_score=round(best["total_score"], 2) if best else self._emergency_only_score(priority, waiting_score),
            decision_reason=decision_reason,
            candidates_count=len(ranked),
            criteria=criteria,
            created_at=datetime.now(UTC),
        )
        emergency.priority = priority
        emergency.state = EmergencyState.PRIORIZADA.value
        self.db.add(recommendation)
        self.db.flush()
        self.events.record(
            EventType.EMERGENCY_PRIORITIZED,
            "La IA heuristica calculo prioridad y ranking de ambulancias.",
            emergency_id=emergency.id,
            ambulance_id=recommendation.recommended_ambulance_id,
            metadata={
                "recommendation_id": recommendation.id,
                "decision_reason": recommendation.decision_reason,
                "candidates_count": recommendation.candidates_count,
                **recommendation.criteria,
            },
        )
        return recommendation

    def _build_criteria(
        self,
        emergency: Emergency,
        priority: int,
        waiting_score: float,
        ranked: list[dict],
        best: dict | None,
    ) -> dict:
        return {
            "weights": self.WEIGHTS,
            "references": {
                "max_distance_km": self.MAX_DISTANCE,
                "max_operational_load": self.MAX_OPERATIONAL_LOAD,
                "max_waiting_minutes": self.MAX_WAITING_SECONDS // 60,
                "availability_scores": self.AVAILABILITY_SCORES,
            },
            "emergency": {
                "severity": emergency.severity,
                "priority": priority,
                "waiting_time_score": round(waiting_score, 2),
            },
            "selected": self._ranking_item(best) if best else None,
            "no_candidate_reason": None if best else "No hay ambulancias disponibles o recuperadas para recomendar.",
            "ranking": [self._ranking_item(item) for item in ranked],
        }

    def _decision_reason(self, best: dict | None) -> str:
        if best is None:
            return "No hay ambulancias disponibles o recuperadas para recomendar."
        ambulance = best["ambulance"]
        return (
            f"{ambulance.code} fue recomendada por obtener el mayor puntaje total "
            f"({round(best['total_score'], 2)}) en el ranking heuristico."
        )

    def _ranking_item(self, item: dict | None) -> dict | None:
        if item is None:
            return None
        ambulance = item["ambulance"]
        return {
            "ambulance_id": ambulance.id,
            "code": ambulance.code,
            "state": ambulance.state,
            "distance": round(item["distance"], 2),
            "operational_load": ambulance.operational_load,
            "reliability": round(float(ambulance.reliability), 2),
            "normalized_scores": {
                criterion: round(score, 2)
                for criterion, score in item["scores"].items()
            },
            "weighted_scores": {
                criterion: round(score, 2)
                for criterion, score in item["weighted_scores"].items()
            },
            "total_score": round(item["total_score"], 2),
        }

    def _severity_score(self, emergency: Emergency) -> int:
        return min(100, emergency.severity * 10)

    def _distance_score(self, distance: float) -> float:
        return self._bounded_score(100.0 * (1.0 - distance / self.MAX_DISTANCE))

    def _availability_score(self, ambulance: AmbulanceNode) -> float:
        return self.AVAILABILITY_SCORES.get(ambulance.state, 0.0)

    def _operational_load_score(self, ambulance: AmbulanceNode) -> float:
        load = min(float(ambulance.operational_load), self.MAX_OPERATIONAL_LOAD)
        return self._bounded_score(100.0 * (1.0 - load / self.MAX_OPERATIONAL_LOAD))

    def _reliability_score(self, ambulance: AmbulanceNode) -> float:
        return self._bounded_score(float(ambulance.reliability) * 100.0)

    def _waiting_time_score(self, emergency: Emergency) -> float:
        if emergency.created_at is None:
            return 0.0
        created_at = emergency.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        elapsed_seconds = max(0.0, (datetime.now(UTC) - created_at).total_seconds())
        return self._bounded_score(100.0 * (elapsed_seconds / self.MAX_WAITING_SECONDS))

    def _emergency_only_score(self, priority: int, waiting_score: float) -> float:
        return round(
            priority * self.WEIGHTS["severity"]
            + waiting_score * self.WEIGHTS["waiting_time"],
            2,
        )

    def _bounded_score(self, value: float) -> float:
        return max(0.0, min(100.0, value))
