import argparse
import json
import logging
import time

import pika

from app.core.config import settings
from simulator.ambulance_node.heartbeat import HeartbeatLoop
from simulator.ambulance_node.node_client import AmbulanceNodeClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Nodo de ambulancia simulado DistriCare")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--code", required=True)
    parser.add_argument("--location", default="0,0")
    parser.add_argument("--load", type=int, default=0)
    parser.add_argument("--reliability", type=float, default=1.0)
    parser.add_argument("--heartbeat-interval", type=int, default=5)
    parser.add_argument("--accept-all", action="store_true", help="Intenta aceptar cualquier emergencia publicada.")
    return parser


def should_attempt(payload: dict, ambulance_id: str | None, accept_all: bool) -> bool:
    if accept_all:
        return True
    return payload.get("recommended_ambulance_id") == ambulance_id


def consume_events(client: AmbulanceNodeClient, accept_all: bool) -> None:
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.exchange_declare(exchange=settings.rabbitmq_exchange, exchange_type="topic", durable=True)
    queue = channel.queue_declare(queue=f"ambulance.{client.code}", durable=True).method.queue
    channel.queue_bind(exchange=settings.rabbitmq_exchange, queue=queue, routing_key="emergency.prioritized")

    def on_message(ch, method, properties, body):
        payload = json.loads(body.decode("utf-8"))
        emergency_id = payload["emergency_id"]
        client.report_node_event(
            "received",
            emergency_id,
            decision="received",
            result="received",
            payload=payload,
        )
        if should_attempt(payload, client.ambulance_id, accept_all):
            result = client.attempt_assignment(emergency_id)
            client.report_node_event(
                "processed",
                emergency_id,
                decision="attempted",
                result="accepted" if result.get("accepted") else "rejected",
                detail=result.get("reason"),
                payload=payload,
            )
            logger.info("Intento de asignacion para %s: %s", emergency_id, result)
        else:
            client.report_node_event(
                "processed",
                emergency_id,
                decision="ignored",
                result="not_recommended",
                detail="La emergencia no fue recomendada para este nodo.",
                payload=payload,
            )
            logger.info("Emergencia %s recibida pero no recomendada para este nodo.", emergency_id)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue, on_message_callback=on_message)
    logger.info("Nodo %s escuchando eventos RabbitMQ.", client.code)
    channel.start_consuming()


def main() -> None:
    args = build_parser().parse_args()
    client = AmbulanceNodeClient(args.api_url, args.code, args.location, args.load, args.reliability)
    client.register()
    heartbeat = HeartbeatLoop(client, args.heartbeat_interval)
    heartbeat.start()
    while True:
        try:
            consume_events(client, args.accept_all)
        except KeyboardInterrupt:
            heartbeat.stop()
            raise
        except Exception as exc:
            logger.warning("Conexion al broker perdida: %s. Reintentando...", exc)
            time.sleep(3)


if __name__ == "__main__":
    main()
