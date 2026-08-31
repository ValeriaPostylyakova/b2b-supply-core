from celery.result import AsyncResult
from django.db.models import Avg, Count, Max, Min, Sum
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import (
    IsBuyer,
    IsSupplier,
)
from apps.orders.models import FileDocument, Order
from apps.orders.paginations import OrderNumberPagination
from apps.orders.permissions import IsNotWarehouseRole, IsOrderParticipant
from apps.orders.serializers import (
    FileDocumentSerializer,
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderFilter,
    OrderListSerializer,
    OrderReportsSerializer,
)
from apps.orders.services import OrderService
from apps.orders.tasks import generate_invoice


class OrdersViewSet(ModelViewSet):
    queryset = Order.objects.select_related("buyer", "supplier").all()
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotWarehouseRole]
    pagination_class = OrderNumberPagination
    filterset_class = OrderFilter

    lookup_field = "external_id"

    def get_permissions(self):
        base_permissions = super().get_permissions()
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        elif self.action in ["create"]:
            return [IsBuyer]
        elif self.action in ["cancel", "documents", "reports"]:
            return [IsOrderParticipant]
        elif self.action in ["confirm", "invoice", "invoice_status"]:
            return [IsSupplier]

        return base_permissions

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action in ["retrieve", "create"]:
            queryset = queryset.prefetch_related("items__product", "items__warehouse")

        if self.request.user.is_buyer:
            queryset = queryset.filter(buyer=self.request.user.organization)
        elif self.request.user.is_supplier:
            queryset = queryset.filter(supplier=self.request.user.organization)

        return queryset

    def get_serializer_class(self):
        if self.action in ["retrieve"]:
            return OrderDetailSerializer
        if self.action in ["create"]:
            return OrderCreateSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        supplier = serializer.validated_data["supplier"]
        items = serializer.validated_data["items"]
        buyer = request.user.organization
        order = OrderService.create_order_with_reservations(buyer, supplier, items)

        optimized_order = self.get_queryset().get(pk=order.pk)
        response_serializer = OrderDetailSerializer(optimized_order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
    )
    def cancel(self, request, external_id=None):
        order = self.get_object()

        if order.status in [
            Order.StatusChoices.CANCELLED,
            Order.StatusChoices.CONFIRMED,
        ]:
            return Response(
                {"detail": "Данный заказ не может быть отменен"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        OrderService.cancel_order(order.id)
        return Response({"detail": "Заказ успешно отменен"}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
    )
    def confirm(self, request, external_id=None):
        order = self.get_object()

        if order.status != Order.StatusChoices.RESERVED:
            return Response(
                {"detail": "Данный заказ не может быть подтвержден"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        OrderService.confirm_order(order.id)
        return Response(
            {"detail": "Заказ успешно подтвержден"}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def invoice(self, request, external_id=None):
        order = self.get_object()

        if order.status != Order.StatusChoices.CONFIRMED:
            return Response(
                {"detail": "Данный заказ не может быть выписан"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task = generate_invoice.delay(order.id)

        return Response(
            {
                "task_id": task.id,
                "status": "In Progress",
                "message": "Генерация отчета запущена в фоновом режиме.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"], url_path="invoice-status/(?P<task_id>[^/.]+)")
    def invoice_status(self, request, external_id=None, task_id=None):
        task_result = AsyncResult(task_id)
        if task_result.status in ["PENDING", "RECEIVED"]:
            return Response(
                {"status": "Pending", "message": "Задача ожидает в очереди"}
            )

        elif task_result.status == "STARTED":
            return Response({"status": "Processing", "message": "Документ формируется"})

        elif task_result.status == "SUCCESS":
            doc_id = task_result.result

            try:
                document = FileDocument.objects.get(id=doc_id)
                serializer = FileDocumentSerializer(document)

                return Response(
                    {"status": "Completed", "document": serializer.data},
                    status=status.HTTP_200_OK,
                )

            except FileDocument.DoesNotExist:
                return Response(
                    {
                        "status": "Failed",
                        "detail": "Документ был создан в MinIO, но запись в БД не найдена.",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        elif task_result.status == "FAILURE":
            return Response(
                {
                    "status": "Failed",
                    "detail": "Произошла ошибка при генерации PDF.",
                    "error": str(task_result.info),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"status": task_result.status})

    @action(
        detail=True,
        methods=["get"],
    )
    def documents(self, request, external_id=None):
        order = self.get_object()
        documents = OrderService.get_order_documents(order.id)
        serializer = FileDocumentSerializer(documents, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    @action(
        detail=False,
        methods=["get"],
    )
    def reports(self, request):
        base_queryset = self.get_queryset()
        report_data = base_queryset.aggregate(
            orders_count=Count("id"),
            orders_total_amount=Sum("total_amount"),
            average_order_amount=Avg("total_amount"),
            min_order_amount=Min("total_amount"),
            max_order_amount=Max("total_amount"),
        )

        serializer = OrderReportsSerializer(report_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
