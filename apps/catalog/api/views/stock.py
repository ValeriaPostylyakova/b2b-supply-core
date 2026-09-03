from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.mixins import UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.permissions import (
    IsSupplierAdminOwner,
    IsSupplierManagerOwner,
    IsWarehouseManagerOwner,
)
from apps.catalog.api.paginations import StockNumberPagination
from apps.catalog.api.serializers.stock import (
    StockListSerializer,
    StockReportsSerializer,
    StockUpdateSerializer,
)
from apps.catalog.models.stock import Stock


class StockViewSet(UpdateModelMixin, ReadOnlyModelViewSet):
    queryset = Stock.objects.all().select_related("warehouse")
    serializer_class = StockListSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsSupplierAdminOwner | IsSupplierManagerOwner | IsWarehouseManagerOwner,
    ]
    pagination_class = StockNumberPagination

    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.action == "partial_update":
            return [
                (
                    permissions.IsAuthenticated
                    & (IsSupplierAdminOwner | IsWarehouseManagerOwner)
                )()
            ]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "partial_update":
            return StockUpdateSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .for_user_organization(self.request.user)
            .with_available_quantity()
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            self.get_object(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        updated_instance = self.get_queryset().get(pk=instance.pk)
        return Response(
            StockListSerializer(updated_instance).data, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"])
    def reports(self, request):
        report_data = self.get_queryset().get_report_data()
        serializer = StockReportsSerializer(report_data)
        return Response(serializer.data)
