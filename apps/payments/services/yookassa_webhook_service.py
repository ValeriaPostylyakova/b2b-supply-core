import logging

from django.db import transaction

from apps.orders.models.order import Order
from apps.payments.models import Payment

logger = logging.getLogger(__name__)


class YooKassaWebhookService:
    @staticmethod
    def process_notification(yk_payment, event_type: str) -> bool:
        payment_id = yk_payment.id

        try:
            payment_attempt = Payment.objects.select_related("order").get(
                external_payment_id=payment_id
            )
        except Payment.DoesNotExist:
            logger.error("Платеж с внешним ID=%s не найден в базе данных", payment_id)
            return False

        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=payment_attempt.order_id)
            payment_attempt.raw_response = yk_payment.json()

            if event_type == "payment.succeeded":
                if payment_attempt.status != "succeeded":
                    payment_attempt.status = "succeeded"
                    payment_attempt.save(update_fields=["status"])

                    order.status = Order.StatusChoices.PAID
                    order.save(update_fields=["status"])

                    logger.info(
                        "Платеж %s успешно завершен. Статус заказа %s изменен на ОПЛАЧЕН",
                        payment_id,
                        order.id,
                    )

                else:
                    logger.info(
                        "Платеж %s уже имел статус 'succeeded', смена статуса пропущена",
                        payment_id,
                    )

            elif event_type == "payment.canceled":
                payment_attempt.status = "canceled"
                payment_attempt.save(update_fields=["status"])

                logger.info(
                    "Платеж %s отменен. Статус заказа %s оставлен без изменений",
                    payment_id,
                    order.id,
                )
            else:
                logger.info(
                    "Получено необрабатываемое событие вебхука: %s для платежа %s",
                    event_type,
                    payment_id,
                )

        return True
