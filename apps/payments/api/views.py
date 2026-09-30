from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.organizations.api.permissions import (
    IsBuyerAdminOwner,
    IsBuyerManagerOwner,
)
from apps.payments.api.serializers import PaymentInitSerializer
from apps.payments.services.yookassa_service import YookassaService


class PaymentView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsBuyerAdminOwner | IsBuyerManagerOwner,
    ]

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
