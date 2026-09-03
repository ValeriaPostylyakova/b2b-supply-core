from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import (
    IsSupplier,
)
from apps.catalog.api.filters.product import ProductFilter
from apps.catalog.api.paginations import ProductNumberPagination
from apps.catalog.api.serializers.product import (
    ProductCreateSerializer,
    ProductListDetailSerializer,
    ProductListSerializer,
    ProductUpdateSerializer,
)
from apps.catalog.models.product import Product
from apps.catalog.selectors.product import ProductSelector


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer()
    lookup_field = "external_id"

    filterset_class = ProductFilter()
    pagination_class = ProductNumberPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductListDetailSerializer
        if self.action == "create":
            return ProductCreateSerializer
        if self.action in ["partial_update"]:
            return ProductUpdateSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsSupplier]
        return super().get_permissions()

    def get_queryset(self):
        selector = ProductSelector(self.queryset, self.request.user, self.action)
        return selector.get_optimized_queryset()

    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user.organization)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
