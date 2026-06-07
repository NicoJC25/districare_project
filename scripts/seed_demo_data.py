from __future__ import annotations

import argparse
import os
from datetime import datetime

import httpx


def post(client: httpx.Client, path: str, payload: dict | None = None) -> dict:
    response = client.post(path, json=payload)
    response.raise_for_status()
    return response.json()


def patch(client: httpx.Client, path: str, payload: dict) -> dict:
    response = client.patch(path, json=payload)
    response.raise_for_status()
    return response.json()


def create_ambulance(client: httpx.Client, code: str, location: str, load: int = 0, reliability: float = 1.0) -> dict:
    return post(
        client,
        "/ambulances",
        {
            "code": code,
            "simulated_location": location,
            "operational_load": load,
            "reliability": reliability,
        },
    )


def create_emergency(client: httpx.Client, emergency_type: str, severity: int, location: str) -> dict:
    return post(
        client,
        "/emergencies",
        {
            "type": emergency_type,
            "severity": severity,
            "simulated_location": location,
        },
    )


def latest_recommendation_for(client: httpx.Client, emergency_id: str) -> dict:
    response = client.get("/recommendations")
    response.raise_for_status()
    for recommendation in response.json():
        if recommendation["emergency_id"] == emergency_id:
            return recommendation
    raise RuntimeError(f"No se encontro recomendacion para emergencia {emergency_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga escenarios demo para DistriCare.")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="URL base de FastAPI.")
    parser.add_argument("--api-key", default=os.getenv("API_KEY"), help="API key para endpoints protegidos.")
    args = parser.parse_args()

    suffix = datetime.now().strftime("%H%M%S")
    headers = {"X-API-Key": args.api_key} if args.api_key else {}
    with httpx.Client(base_url=args.api, headers=headers, timeout=10.0) as client:
        health = client.get("/health")
        health.raise_for_status()

        normal_ambulance = create_ambulance(client, f"AMB-DEMO-NORMAL-{suffix}", "4.7110,-74.0721")
        normal_emergency = create_emergency(client, "Accidente demo", 8, "4.7150,-74.0700")
        normal_recommendation = latest_recommendation_for(client, normal_emergency["id"])
        post(
            client,
            "/assignments/attempt",
            {
                "emergency_id": normal_emergency["id"],
                "ambulance_id": normal_recommendation["recommended_ambulance_id"] or normal_ambulance["id"],
            },
        )

        far = create_ambulance(client, f"AMB-DEMO-FAR-{suffix}", "4.8400,-74.1450")
        create_ambulance(client, f"AMB-DEMO-NEAR-{suffix}", "4.7030,-74.0600")
        mismatch_emergency = create_emergency(client, "Intento distribuido demo", 7, "4.7000,-74.0620")
        post(client, "/assignments/attempt", {"emergency_id": mismatch_emergency["id"], "ambulance_id": far["id"]})

        failing = create_ambulance(client, f"AMB-DEMO-FAIL-{suffix}", "4.6500,-74.0900", reliability=1.0)
        create_ambulance(client, f"AMB-DEMO-BACKUP-{suffix}", "4.6550,-74.0830", reliability=0.95)
        failure_emergency = create_emergency(client, "Reasignacion demo", 9, "4.6520,-74.0880")
        post(client, "/assignments/attempt", {"emergency_id": failure_emergency["id"], "ambulance_id": failing["id"]})
        post(client, f"/ambulances/{failing['id']}/fail")

        closing_ambulance = create_ambulance(client, f"AMB-DEMO-CLOSE-{suffix}", "4.6097,-74.0817")
        closing_emergency = create_emergency(client, "Cierre demo", 6, "4.6105,-74.0800")
        post(client, "/assignments/attempt", {"emergency_id": closing_emergency["id"], "ambulance_id": closing_ambulance["id"]})
        patch(client, f"/emergencies/{closing_emergency['id']}/state", {"state": "EN_ATENCION"})
        patch(client, f"/emergencies/{closing_emergency['id']}/state", {"state": "CERRADA"})

    print("Escenarios demo creados correctamente.")
    print(f"Sufijo de datos: {suffix}")
    print("Revisa Panel General, Asignaciones, Trazabilidad y Eventos del sistema.")


if __name__ == "__main__":
    main()
