import json
import logging
import aio_pika
from django.conf import settings
from django.utils import timezone
from apps.common.models import OutboxEvent

logger = logging.getLogger(__name__)


async def publish_event(event: OutboxEvent):
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    try:
        channel = await connection.channel(
            publisher_confirms=True,
        )

        exchange = await channel.declare_exchange(
            "b2b.events",
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        message = aio_pika.Message(
            body=json.dumps(event.payload).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=str(event.id),
            type=event.event_type,
            headers={
                "event_version": event.event_version,
                "aggregate_id": event.aggregate_id,
            },
        )

        await exchange.publish(
            message,
            routing_key=event.routing_key,
            mandatory=True,
        )

    finally:
        await connection.close()
        
        

async def publish_events_batch(events: list[OutboxEvent]) -> list[OutboxEvent]:
    if not events:
        return []

    published_events = []
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    try:
        channel = await connection.channel(publisher_confirms=True)
        exchange = await channel.declare_exchange(
            "b2b.events",
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        for event in events:
            try:
                message = aio_pika.Message(
                    body=json.dumps(event.payload).encode("utf-8"),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    message_id=str(event.id),
                    type=event.event_type,
                    headers={
                        "event_version": event.event_version,
                        "aggregate_id": str(event.aggregate_id),
                    },
                )

                await exchange.publish(
                    message,
                    routing_key=event.routing_key,
                    mandatory=True,
                )

                event.status = OutboxEvent.Status.PUBLISHED
                event.published_at = timezone.now()
                published_events.append(event)

            except Exception as exc:
                logger.exception(f"Failed to publish OutboxEvent {event.id}: {exc}")
                break

    finally:
        await connection.close()

    return published_events

