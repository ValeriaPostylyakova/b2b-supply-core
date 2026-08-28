from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import (
    IsBuyer,
    IsSupplier,
)
from apps.orders.models import Order
from apps.orders.paginations import OrderNumberPagination
from apps.orders.permissions import IsNotWarehouseRole, IsOrderParticipant
from apps.orders.serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderFilter,
    OrderListSerializer,
)
from apps.orders.services import OrderService


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
        elif self.action in ["cancel", "documents"]:
            return [IsOrderParticipant]
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
                "Данный заказ не может быть отменен", status=status.HTTP_400_BAD_REQUEST
            )

        OrderService.cancel_order(order.id)
        return Response("Заказ успешно отменен", status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
    )
    def confirm(self, request, external_id=None):
        order = self.get_object()

        if order.status != Order.StatusChoices.RESERVED:
            return Response(
                "Данный заказ не может быть подтвержден",
                status=status.HTTP_400_BAD_REQUEST,
            )

        OrderService.confirm_order(order.id)
        return Response("Заказ успешно подтвержден", status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def invoice(self, request, external_id=None):
        order = self.get_object()

    @action(
        detail=True,
        methods=["get"],
    )
    def documents(self, request, external_id=None):
        order = self.get_object()

    @action(
        detail=True,
        methods=["get"],
    )
    def documents_download(self, request, external_id=None):
        pass
