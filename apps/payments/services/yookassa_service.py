import logging
import uuid

from django.conf import settings
from yookassa import Configuration
from yookassa import Payment as YkPayment

from apps.orders.models import Order
from apps.payments.models import Payment

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


logger = logging.getLogger(__name__)


class YookassaService:
    @staticmethod
    def create_payment_session(order: Order) -> str:
        payment_attempt = Payment.objects.create(
            order=order,
            provider="yookassa",
            amount=order.total_amount,
            status="pending",
        )

        idempotence_key = str(uuid.uuid4())

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
            return yk_response.confirmation.confirmation_url

        except Exception as e:
            logger.error(f"Yookassa error: {e!s}", exc_info=True)
            payment_attempt.status = "canceled"
            payment_attempt.raw_response = {"error": str(e)}
            payment_attempt.save()
            raise ValueError(f"Ошибка шлюза ЮKassa: {e}")
