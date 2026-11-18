from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.organizations.api.permissions import (
    IsBuyerAdminOwner,
    IsBuyerManagerOwner,
)
from apps.payments.api.serializers import PaymentInitSerializer
from apps.payments.services.yookassa_service import YookassaService


@extend_schema(tags=["Оплата"])
class PaymentView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsBuyerAdminOwner | IsBuyerManagerOwner,
    ]

    @extend_schema(
        summary="Создать платёж",
        description="Создаёт платёжную сессию YooKassa для заказа в статусе RESERVED. Откройте confirmation_url, чтобы перейти к оплате.",
        request=PaymentInitSerializer,
        examples=[OpenApiExample("Оплата заказа", value={"order_id": "<order_uuid>"}, request_only=True)],
        responses={201: OpenApiResponse(response=inline_serializer(name="PaymentInitResponse", fields={"confirmation_url": serializers.URLField()}), description="Ссылка на оплату.")},
    )
    def post(self, request):
        serializer = PaymentInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = get_object_or_404(
            Order, external_id=serializer.validated_data["order_id"]
        )

        try:
            confirmation_url = YookassaService.create_payment_session(order)
            return Response(
                {"confirmation_url": confirmation_url}, status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
