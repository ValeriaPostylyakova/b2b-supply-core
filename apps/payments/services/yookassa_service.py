import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from yookassa import Configuration
from yookassa import Payment as YkPayment

from apps.orders.models import Order
from apps.orders.tasks.reservation import clear_expired_reservation_task
from apps.payments.models import Payment

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


logger = logging.getLogger(__name__)


class YookassaService:
    @staticmethod
    def create_payment_session(order: Order) -> str:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk)

            if order.status == Order.StatusChoices.PAID:
                raise ValueError("Заказ уже оплачен")

            expiry_time = timezone.now() + timedelta(minutes=10)
            order.reservations.update(expires_at=expiry_time)

            payment_attempt = Payment.objects.create(
                order=order,
                provider="yookassa",
                amount=order.total_amount,
                status="pending",
            )

        idempotence_key = str(uuid.uuid4())

        expires_at_iso = expiry_time.isoformat()

        try:
            yk_response = YkPayment.create(
                {
                    "amount": {"value": str(payment_attempt.amount), "currency": "RUB"},
                    "confirmation": {
                        "type": "redirect",
                        "return_url": f"{settings.FRONTEND_URL}/orders/{order.id}/status/",
                    },
                    "capture": True,
                    "description": f"Оплата заказа №{order.id}. Попытка №{payment_attempt.id}",
                    "expires_at": expires_at_iso,
                },
                idempotence_key,
            )

            payment_attempt.external_payment_id = yk_response.id

            if hasattr(yk_response, "json"):
                payment_attempt.raw_response = (
                    yk_response.json() if callable(yk_response.json) else yk_response
                )
            else:
                payment_attempt.raw_response = dict(yk_response)

            payment_attempt.save()

            transaction.on_commit(
                lambda: clear_expired_reservation_task.apply_async(
                    args=[order.id], countdown=600
                )
            )

            return yk_response.confirmation.confirmation_url

        except Exception as e:
            logger.error(f"Yookassa error: {e!s}", exc_info=True)

            payment_attempt.status = "canceled"
            payment_attempt.raw_response = {"error": str(e)}
            payment_attempt.save()
            raise ValueError(f"Ошибка шлюза ЮKassa: {e}")
