from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models.order import Order
from apps.orders.services.order_invoice import InvoiceService
from apps.organizations.api.permissions import IsSupplier


class OrderInvoiceView(APIView):
    permission_classes = [IsSupplier]

    def post(self, request, external_id):
        order = get_object_or_404(Order, external_id=external_id)
        task_id = InvoiceService.generate_invoice(order.id, order.status)

        return Response(
            {
                "task_id": task_id,
                "status": "In Progress",
                "message": "Генерация отчета запущена в фоновом режиме.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    def get(self, request, task_id):
        data = InvoiceService.get_invoice_status(task_id)

        if data.get("status") == "Failed":
            return Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(data, status=status.HTTP_200_OK)
