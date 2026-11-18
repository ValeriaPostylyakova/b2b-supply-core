from django.utils import timezone

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import transaction
from django.db.models import F

from apps.orders.models import Order
from apps.orders.models.reservation import Reservation
from apps.catalog.models.stock import Stock

logger = get_task_logger(__name__)


def _cancel_expired_order(order_id: int) -> str:
    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(pk=order_id)
        except Order.DoesNotExist:
            logger.error(f"[Ошибка] Заказ №{order_id} не найден в базе данных.")
            return f"Заказ {order_id} не найден."

        if order.status == Order.StatusChoices.PAID:
            logger.info(
                f"[Пропуск] Заказ №{order_id} уже оплачен. Отмена не требуется."
            )
            return f"Заказ {order_id} уже оплачен. Отмена не требуется."

        if order.status == Order.StatusChoices.RESERVED:
            logger.info(
                f"[Действие] Время ожидания оплаты истекло. Начинается отмена заказа №{order_id}..."
            )

            order.status = Order.StatusChoices.CANCELLED
            order.save(update_fields=["status", "updated_at"])
            logger.info(f"[Статус] Статус заказа №{order_id} изменен на CANCELLED.")

            reservations = list(
                order.reservations.filter(status=Reservation.Status.ACTIVE).order_by("stock_id")
            )

            if not reservations:
                logger.warning(
                    f"[Предупреждение] У заказа №{order_id} нет активных резерваций для возврата."
                )

            stock_ids = [r.stock_id for r in reservations]
            stocks_map = {
                s.id: s
                for s in Stock.objects.select_for_update().filter(id__in=stock_ids).order_by("id")
            }

            for reservation in reservations:
                stock = stocks_map[reservation.stock_id]

                stock.reserved_quantity = max(0, stock.reserved_quantity - reservation.quantity)
                stock.save(update_fields=["reserved_quantity"])

                reservation.status = Reservation.Status.EXPIRED
                reservation.save(update_fields=["status"])

                logger.info(
                    f"[Склад] Товар (Stock ID: {stock.id}) в количестве {reservation.quantity} шт. "
                    f"возвращен на склад по заказу №{order_id}."
                )

            logger.info(
                f"[Успех] Заказ №{order_id} успешно отменен. Освобождено позиций: {len(reservations)}."
            )
            return f"Заказ {order_id} отменен, остатки возвращены на склад."

        logger.info(
            f"[Пропуск] Заказ №{order_id} имеет статус '{order.status}'. "
            f"Автоматическая отмена не требуется."
        )
        return f"Заказ {order_id} находится в статусе {order.status}, отмена пропущена."


@shared_task(
    name="orders.clear_expired_reservation",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def clear_expired_reservation_task(self, order_id=None):
    try:
        if order_id is not None:
            logger.info(
                f"[Запуск] Задача проверки истечения времени резерва для заказа №{order_id}"
            )
            return _cancel_expired_order(order_id)

        logger.info("[Запуск] Плановая проверка просроченных резервов заказов...")
        now = timezone.now()

        expired_order_ids = list(
            Order.objects.filter(
                status=Order.StatusChoices.RESERVED,
                reservations__status=Reservation.Status.ACTIVE,
                reservations__expires_at__lte=now,
            )
            .distinct()
            .values_list("id", flat=True)
        )

        if not expired_order_ids:
            logger.info("[Пропуск] Просроченных заказов не найдено.")
            return "Просроченных заказов не найдено."

        for oid in expired_order_ids:
            _cancel_expired_order(oid)

        summary = f"Обработано просроченных заказов: {len(expired_order_ids)}."
        logger.info(f"[Успех] {summary}")
        return summary

    except Exception as exc:
        logger.error(
            f"[Сбой] Критическая ошибка при обработке резервов (order_id={order_id}): {exc!s}. "
            f"Попытка повтора задачи №{self.request.retries + 1}."
        )
        raise self.retry(exc=exc)