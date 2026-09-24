import logging

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.catalog.models.stock import Stock
from apps.orders.models.reservation import Reservation

logger = logging.getLogger(__name__)


@shared_task(name="orders.clear_expired_reservations", bind=True, max_retries=3)
def clear_expired_reservations_task(self):
    now = timezone.now()
    batch_size = 200

    logger.info(
        "Запуск очистки просроченных броней. Поиск пакета до %s шт.", batch_size
    )

    expired_ids = list(
        Reservation.objects.filter(
            status=Reservation.Status.ACTIVE, expired_at__lte=now
        ).values_list("id", flat=True)[:batch_size]
    )

    if not expired_ids:
        logger.info("Просроченных броней не обнаружено. Завершение задачи.")
        return {"processed": 0}

    logger.info(
        "Найдено %s потенциально просроченных броней для обработки.", len(expired_ids)
    )

    processed = 0
    try:
        with transaction.atomic():
            reservations = list(
                Reservation.objects.select_for_update(skip_locked=True)
                .select_related("stock")
                .filter(id__in=expired_ids, status=Reservation.Status.ACTIVE)
            )

            if not reservations:
                logger.warning(
                    "Все найденные брони %s уже заблокированы или обработаны в другой транзакции.",
                    expired_ids,
                )
                return {"processed": 0}

            for reservation in reservations:
                Stock.objects.filter(id=reservation.stock_id).update(
                    reserved_quantity=F("reserved_quantity") - reservation.quantity
                )

            current_batch_ids = [r.id for r in reservations]
            updated = Reservation.objects.filter(id__in=current_batch_ids).update(
                status=Reservation.Status.EXPIRED
            )
            processed = updated

    except Exception as exc:
        logger.exception(
            "Ошибка при обработке пакета просроченных броней. ID для обработки: %s. Попытка ретрая...",
            expired_ids,
        )
        raise self.retry(exc=exc, countdown=min(2**self.request.retries * 5, 60))

    logger.info(
        "Успешно переведено в статус EXPIRED броней: %s из %s запрошенных.",
        processed,
        len(expired_ids),
    )

    if len(expired_ids) == batch_size:
        logger.info(
            "Достигнут лимит пакета (%s). Запуск следующей задачи для обработки оставшихся броней.",
            batch_size,
        )
        clear_expired_reservations_task.apply_async(countdown=0)

    return {"processed": processed}
