import logging

import httpx

logger = logging.getLogger(__name__)


class AmbulanceNodeClient:
    def __init__(self, api_url: str, code: str, location: str, load: int, reliability: float):
        self.api_url = api_url.rstrip("/")
        self.code = code
        self.location = location
        self.load = load
        self.reliability = reliability
        self.ambulance_id: str | None = None

    def check_backend(self) -> None:
        try:
            response = httpx.get(f"{self.api_url}/health", timeout=5)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise RuntimeError(f"Backend no esta listo: {detail}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"No se pudo conectar al backend en {self.api_url}. "
                "Verifica que uvicorn este corriendo y que PostgreSQL este disponible."
            ) from exc

    def register(self) -> str:
        self.check_backend()
        response = httpx.post(
            f"{self.api_url}/ambulances",
            json={
                "code": self.code,
                "simulated_location": self.location,
                "operational_load": self.load,
                "reliability": self.reliability,
            },
            timeout=10,
        )
        response.raise_for_status()
        self.ambulance_id = response.json()["id"]
        logger.info("Nodo %s registrado con id %s", self.code, self.ambulance_id)
        return self.ambulance_id

    def heartbeat(self) -> None:
        if not self.ambulance_id:
            self.register()
        response = httpx.post(f"{self.api_url}/ambulances/{self.ambulance_id}/heartbeat", timeout=5)
        response.raise_for_status()

    def attempt_assignment(self, emergency_id: str) -> dict:
        if not self.ambulance_id:
            self.register()
        response = httpx.post(
            f"{self.api_url}/assignments/attempt",
            json={"emergency_id": emergency_id, "ambulance_id": self.ambulance_id},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    def report_node_event(
        self,
        stage: str,
        emergency_id: str | None,
        *,
        decision: str | None = None,
        result: str | None = None,
        detail: str | None = None,
        payload: dict | None = None,
    ) -> None:
        if not self.ambulance_id:
            self.register()
        response = httpx.post(
            f"{self.api_url}/ambulances/{self.ambulance_id}/node-events",
            json={
                "stage": stage,
                "emergency_id": emergency_id,
                "decision": decision,
                "result": result,
                "detail": detail,
                "payload": payload or {},
            },
            timeout=5,
        )
        response.raise_for_status()
