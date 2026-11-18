from uuid import UUID

from django.db.models import Q
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.orders.api.filters import OrderFilter
from apps.orders.api.paginations import OrderNumberPagination
from apps.orders.api.permissions import IsNotWarehouseRole
from apps.orders.api.serializers.order import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    OrderReportsSerializer,
)
from apps.orders.models import Order
from apps.orders.services.order import OrderService
from apps.organizations.api.permissions import (
    IsBuyer,
    IsSupplier,
    IsVerifyOrganization,
)


@extend_schema_view(
    list=extend_schema(
        summary="Список заказов",
        description="Возвращает заказы, в которых текущая организация выступает покупателем или поставщиком.",
    ),
    retrieve=extend_schema(
        summary="Карточка заказа",
        description="Возвращает заказ, состав позиций, цены и суммы.",
    ),
    update=extend_schema(
        summary="Изменить заказ", description="Административное обновление заказа."
    ),
    partial_update=extend_schema(
        summary="Изменить заказ частично",
        description="Административное частичное обновление заказа.",
    ),
    destroy=extend_schema(
        summary="Удалить заказ", description="Административное удаление заказа."
    ),
)
@extend_schema(tags=["Заказы"])
class OrderViewSet(ModelViewSet):
    queryset = (
        Order.objects.select_related("buyer", "supplier").all().order_by("-created_at")
    )
    serializer_class = OrderListSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotWarehouseRole,
        IsVerifyOrganization,
    ]
    pagination_class = OrderNumberPagination
    filterset_class = OrderFilter

    lookup_field = "external_id"

    def get_permissions(self):
        base_permissions = super().get_permissions()
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        elif self.action in ["create", "cancel"]:
            return [IsBuyer]
        elif self.action in ["confirm"]:
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

    @extend_schema(
        summary="Создать заказ",
        description="Доступно покупателю. Передайте supplier UUID и список позиций с product UUID, warehouse UUID и quantity. При создании система резервирует остатки.",
        request=OrderCreateSerializer,
        examples=[
            OpenApiExample(
                "Новый заказ",
                value={
                    "supplier": "<supplier_uuid>",
                    "items": [
                        {
                            "product": "<product_uuid>",
                            "warehouse": "<warehouse_uuid>",
                            "quantity": 5,
                        }
                    ],
                },
                request_only=True,
            )
        ],
        responses={
            201: OpenApiResponse(
                response=OrderDetailSerializer,
                description="Заказ создан, остатки зарезервированы.",
            )
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        supplier = serializer.validated_data["supplier"]
        items = serializer.validated_data["items"]
        buyer = request.user.organization

        order = OrderService.create_order_with_reservations(buyer, supplier, items)

        optimized_order = self.get_queryset().get(pk=order.pk)
        response_serializer = OrderDetailSerializer(
            optimized_order, context=self.get_serializer_context()
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Отменить заказ",
        description="Покупатель отменяет заказ. Статус станет CANCELLED, зарезервированные остатки будут освобождены.",
        request=None,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="OrderCancelResponse",
                    fields={
                        "detail": serializers.CharField(default="Заказ успешно отменен")
                    },
                ),
                description="Заказ успешно отменен",
            ),
            400: OpenApiResponse(
                description="Заказ нельзя отменить из текущего статуса"
            ),
            404: OpenApiResponse(description="Заказ с таким идентификатором не найден"),
        },
    )
    @action(
        detail=True,
        methods=["post"],
    )
    def cancel(self, request, external_id=None):
        order = self.get_object()

        OrderService.cancel_order(order)
        return Response({"detail": "Заказ успешно отменен"}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Подтвердить заказ",
        description="Поставщик подтверждает заказ. Доступно для заказа в допустимом бизнес-статусе.",
        request=None,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="OrderConfirmResponse",
                    fields={
                        "detail": serializers.CharField(
                            default="Заказ успешно подтвержден"
                        )
                    },
                ),
                description="Заказ успешно подтвержден",
            ),
            400: OpenApiResponse(
                description="Ошибка валидации при подтверждении заказа"
            ),
            404: OpenApiResponse(description="Заказ не найден"),
        },
    )
    @action(
        detail=True,
        methods=["post"],
    )
    def confirm(self, request, external_id=None):
        order = self.get_object()

        OrderService.confirm_order(order)
        return Response(
            {"detail": "Заказ успешно подтвержден"}, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Получение отчетов по заказам",
        description="Возвращает агрегированные аналитические данные по заказам организации.",
        responses={
            200: OrderReportsSerializer,
        },
    )
    @action(
        detail=False,
        methods=["get"],
    )
    def reports(self, request):
        report_data = self.get_queryset().get_report_data()
        serializer = OrderReportsSerializer(report_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Заказы"])
class OrderExistsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Проверить доступ к заказу",
        description="200 — заказ существует и доступен текущей организации; 404 — не найден или нет доступа.",
    )
    def get(self, request, external_id: UUID):
        order_exists = Order.objects.filter(
            Q(buyer=request.user.organization) | Q(supplier=request.user.organization),
            external_id=external_id,
        ).exists()

        if not order_exists:
            return Response(
                {"detail": "Заказ не найден или у вас нет к нему доступа."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(status=status.HTTP_200_OK)
