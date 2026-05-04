import json
import logging

import pika

from app.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def publish(self, routing_key: str, payload: dict) -> bool:
        try:
            params = pika.URLParameters(settings.rabbitmq_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(
                exchange=settings.rabbitmq_exchange,
                exchange_type="topic",
                durable=True,
            )
            channel.basic_publish(
                exchange=settings.rabbitmq_exchange,
                routing_key=routing_key,
                body=json.dumps(payload).encode("utf-8"),
                properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
            )
            connection.close()
            return True
        except Exception as exc:  # RabbitMQ is optional for unit tests and local model work.
            logger.warning("RabbitMQ publish skipped: %s", exc)
            return False
