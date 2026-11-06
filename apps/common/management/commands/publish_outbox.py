import asyncio

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.common.models import OutboxEvent
from apps.common.services.outbox_publisher import publish_event


class Command(BaseCommand):
    help = "Publish pending Outbox events to RabbitMQ"

    def handle(self, *args, **options):
        self.stdout.write("Outbox publisher started")

        while True:
            event_id = None

            with transaction.atomic():
                event = (
                    OutboxEvent.objects.select_for_update(skip_locked=True)
                    .filter(status=OutboxEvent.Status.PENDING)
                    .order_by("created_at")
                    .first()
                )

                if event:
                    event_id = event.id

                    try:
                        asyncio.run(publish_event(event))

                        event.status = OutboxEvent.Status.PUBLISHED
                        event.published_at = timezone.now()
                        event.save(
                            update_fields=[
                                "status",
                                "published_at",
                            ]
                        )

                        self.stdout.write(
                            self.style.SUCCESS(f"Published event {event.id}")
                        )

                    except Exception as exc:
                        self.stderr.write(f"Failed to publish {event.id}: {exc}")

            if event_id is None:
                break
