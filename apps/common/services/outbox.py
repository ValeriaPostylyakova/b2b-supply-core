from apps.common.models import OutboxEvent


def create_outbox_event(
    *,
    event_type: str,
    aggregate_id: str,
    routing_key: str,
    payload: dict,
) -> OutboxEvent:

    return OutboxEvent.objects.create(
        event_type=event_type,
        aggregate_id=str(aggregate_id),
        routing_key=routing_key,
        payload=payload,
    )
