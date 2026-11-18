from django.core.cache import cache
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.catalog.api.filters.product import ProductFilter
from apps.catalog.api.paginations import ProductNumberPagination
from apps.catalog.api.serializers.product import (
    ProductCreateSerializer,
    ProductListDetailSerializer,
    ProductListSerializer,
    ProductUpdateSerializer,
)
from apps.catalog.infrastructure.cache import (
    build_products_cache_key,
    invalidate_products_cache,
    product_detail_cache_key,
)
from apps.catalog.models.product import Product
from apps.catalog.selectors.product import ProductSelector
from apps.organizations.api.permissions import IsSupplier, IsVerifyOrganization


@extend_schema_view(
    create=extend_schema(summary="Создать товар", description="Создаёт товар от имени организации-поставщика. Поставщик определяется по текущему пользователю.", examples=[OpenApiExample("Новый товар", value={"sku": "SKU-001", "name": "Кабель силовой", "price": "1250.00", "description": "Медный кабель"}, request_only=True)]),
    update=extend_schema(summary="Изменить товар", description="Полностью обновляет доступные поля товара поставщика."),
    partial_update=extend_schema(summary="Изменить товар частично", description="Обновляет переданные поля товара поставщика."),
    destroy=extend_schema(summary="Архивировать товар", description="Деактивирует товар; физически запись не удаляется."),
)
@extend_schema(tags=["Товары"])
class ProductViewSet(ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer
    lookup_field = "external_id"

    filterset_class = ProductFilter
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
            return [permissions.IsAuthenticated(), IsSupplier, IsVerifyOrganization()]
        return super().get_permissions()

    def get_queryset(self):
        selector = ProductSelector(self.queryset, self.request.user, self.action)
        return selector.get_optimized_queryset()

    @extend_schema(summary="Список товаров", description="Постраничный каталог. Фильтры: `search` — поиск по названию/SKU; `min_price`, `max_price` — диапазон цены; `available=true|false` — наличие доступного остатка; `ordering=price|-price|name|-name|created_at|-created_at` — сортировка. Пример: `?search=кабель&available=true&min_price=100&ordering=price`.")
    def list(self, request, *args, **kwargs):
        cache_key = build_products_cache_key(request)

        cache_data = cache.get(cache_key)
        if cache_data is not None:
            return Response(cache_data)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=300)
        return response

    @extend_schema(summary="Карточка товара", description="Подробная карточка товара с остатками по складам.")
    def retrieve(self, request, *args, **kwargs):
        cache_key = product_detail_cache_key(kwargs["external_id"])

        cache_data = cache.get(cache_key)
        if cache_data is not None:
            return Response(cache_data)

        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=300)
        return response

    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user.organization)
        invalidate_products_cache()

    def perform_update(self, serializer):
        instance = serializer.save()
        cache_key = product_detail_cache_key(instance.pk)
        cache.delete(cache_key)
        invalidate_products_cache()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

        cache_key = product_detail_cache_key(instance.pk)
        cache.delete(cache_key)
        invalidate_products_cache()
