from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import transaction
from django.db.models import F

from apps.orders.models import Order
from apps.orders.models.reservation import Reservation

logger = get_task_logger(__name__)


@shared_task(
    name="orders.clear_expired_reservation",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def clear_expired_reservation_task(self, order_id):
    logger.info(
        f"[Запуск] Задача проверки истечения времени резерва для заказа №{order_id}"
    )

    try:
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
                order.save()
                logger.info(f"[Статус] Статус заказа №{order_id} изменен на CANCELLED.")

                reservations = order.reservations.filter(status="active")
                reservations_count = reservations.count()

                if not reservations_count:
                    logger.warning(
                        f"[Предупреждение] У заказа №{order_id} нет активных резерваций для возврата."
                    )

                for reservation in reservations:
                    stock = reservation.stock

                    stock.quantity = F("quantity") + reservation.quantity
                    stock.save()

                    reservation.status = Reservation.Status.EXPIRED
                    reservation.save()

                    logger.info(
                        f"[Склад] Товар (Stock ID: {stock.id}) в количестве {reservation.quantity} шт. "
                        f"возвращен на склад по заказу №{order_id}."
                    )

                logger.info(
                    f"[Успех] Заказ №{order_id} успешно отменен. Освобождено позиций: {reservations_count}."
                )
                return f"Заказ {order_id} отменен, остатки возвращены на склад."

            logger.info(
                f"[Пропуск] Заказ №{order_id} имеет статус '{order.status}'. "
                f"Автоматическая отмена не требуется."
            )
            return f"Заказ {order_id} находится в статусе {order.status}, отмена пропущена."

    except Exception as exc:
        logger.error(
            f"[Сбой] Критическая ошибка при обработке заказа №{order_id}: {exc!s}. "
            f"Попытка повтора задачи №{self.request.retries + 1}."
        )
        raise self.retry(exc=exc)
