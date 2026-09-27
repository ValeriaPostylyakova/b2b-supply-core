import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from yookassa.domain.notification import WebhookNotificationFactory

from apps.orders.models import Order
from apps.payments.api.serializers import PaymentInitSerializer
from apps.payments.infrastructure.locks import redis_webhook_lock
from apps.payments.services.yookassa_service import YookassaService
from apps.payments.services.yookassa_webhook_service import YooKassaWebhookService

logger = logging.getLogger(__name__)


class InitPaymentView(APIView):
    def post(self, request):
        serializer = PaymentInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = Order.objects.get(external_id=serializer.validated_data["order_id"])

        try:
            confirmation_url = YookassaService.create_payment_session(order)
            return Response(
                {"confirmation_url": confirmation_url}, status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class YookassaWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.info("Получен входящий вебхук от ЮKassa")

        try:
            notification = WebhookNotificationFactory().create(request.data)
        except Exception as e:
            logger.warning(
                "Получена невалидная полезная нагрузка вебхука. Ошибка: %s", str(e)
            )
            return Response(
                {"error": "Невалидная полезная нагрузка"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        yk_payment = notification.object
        payment_id = yk_payment.id
        event_type = notification.event

        try:
            with redis_webhook_lock(payment_id, expire_seconds=30):
                is_processed = YooKassaWebhookService.process_notification(
                    yk_payment, event_type
                )

                if not is_processed:
                    return Response(
                        {
                            "status": "ignored",
                            "detail": "Платеж не найден в базе данных",
                        },
                        status=status.HTTP_200_OK,
                    )

            return Response({"status": "success"}, status=status.HTTP_200_OK)

        except ValueError:
            return Response({"status": "already processing"}, status=status.HTTP_200_OK)

        except Exception:
            logger.exception(
                "Критическая ошибка при обработке вебхука для платежа %s", payment_id
            )
            return Response(
                {"error": "Внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
