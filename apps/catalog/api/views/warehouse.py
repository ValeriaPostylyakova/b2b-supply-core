from django.db.models import Count
from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet

from apps.catalog.api.filters.warehouse import WarehouseFilter
from apps.catalog.api.paginations import ProductNumberPagination
from apps.catalog.api.serializers.warehouse import (
    WarehouseCreateUpdateSerializer,
    WarehouseListSerializer,
)
from apps.catalog.models.warehouse import Warehouse
from apps.organizations.api.permissions import (
    IsSupplierAdminOwner,
)


class WarehouseViewSet(ModelViewSet):
    queryset = Warehouse.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WarehouseListSerializer
    filterset_class = WarehouseFilter
    pagination_class = ProductNumberPagination

    lookup_field = "external_id"

    def get_permissions(self):
        base_permissions = super().get_permissions()
        if self.action in ["create", "update", "partial_update", "destroy"]:
            base_permissions.append(IsSupplierAdminOwner())
        return base_permissions

    def get_queryset(self):
        queryset = self.queryset.filter(is_active=True)
        user = self.request.user
        if user.is_buyer and user.has_organization:
            queryset = queryset.select_related("supplier")
        else:
            queryset = queryset.filter(supplier=user.organization).annotate(
                products_count=Count("stocks__product", distinct=True)
            )
        return queryset

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return WarehouseCreateUpdateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user.organization)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
