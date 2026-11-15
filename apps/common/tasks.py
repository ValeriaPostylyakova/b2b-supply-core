import asyncio
import logging
from celery import shared_task
from django.db import transaction

from apps.common.models import OutboxEvent
from apps.common.services.outbox_publisher import publish_events_batch

logger = logging.getLogger(__name__)


@shared_task(name="common.publish_outbox_events")
def publish_outbox_events(batch_size: int = 100):
    with transaction.atomic():
        events = list(
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(status=OutboxEvent.Status.PENDING)
            .order_by("created_at")[:batch_size]
        )

        if not events:
            return 0

        published_events = asyncio.run(publish_events_batch(events))

        if published_events:
            OutboxEvent.objects.bulk_update(    
                published_events,
                fields=["status", "published_at"],
            )
            logger.info(f"Published {len(published_events)} outbox events.")

        return len(published_events)
