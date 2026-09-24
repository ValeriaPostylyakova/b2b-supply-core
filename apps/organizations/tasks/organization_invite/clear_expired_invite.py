import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.organizations.models.organization_invite import OrganizationInvite

logger = logging.getLogger(__name__)


@shared_task(name="organizations.clear_expired_invite", bind=True, max_retries=3)
def clear_expired_invite_task(self):
    now = timezone.now()
    batch_size = 200

    logger.info(
        "Запуск очистки просроченных заявок на организацию. Поиск пакета до %s шт.",
        batch_size,
    )

    expired_ids = list(
        OrganizationInvite.objects.filter(
            status=OrganizationInvite.Status.PENDING, expires_at__lte=now
        ).values_list("id", flat=True)[:batch_size]
    )

    if not expired_ids:
        logger.info(
            "Просроченных заявок на организацию не обнаружено. Завершение задачи."
        )
        return {"processed": 0}

    logger.info(
        "Найдено %s потенциально просроченных заявок на организацию для обработки.",
        len(expired_ids),
    )

    processed = 0
    try:
        with transaction.atomic():
            invites = list(
                OrganizationInvite.objects.select_for_update(skip_locked=True).filter(
                    id__in=expired_ids, status=OrganizationInvite.Status.PENDING
                )
            )

            if not invites:
                return {"processed": 0}

            current_batch_ids = [i.id for i in invites]

            processed = OrganizationInvite.objects.filter(
                id__in=current_batch_ids
            ).update(status=OrganizationInvite.Status.EXPIRED)

    except Exception as exc:
        logger.exception(
            "Ошибка при обработке пакета просроченных заявок на организацию. ID для обработки: %s. Попытка ретрая...",
            expired_ids,
        )
        raise self.retry(exc=exc, countdown=min(2**self.request.retries * 5, 60))

    logger.info(
        "Успешно переведено в статус EXPIRED заявок на организацию: %s из %s запрошенных.",
        processed,
        len(expired_ids),
    )

    if len(expired_ids) == batch_size:
        logger.info(
            "Достигнут лимит пакета (%s). Запуск следующей задачи для обработки оставшихся заявок на организацию.",
            batch_size,
        )
        clear_expired_invite_task.apply_async(countdown=0)

    return {"processed": processed}
