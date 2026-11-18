from django.db.models import Count
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
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
    IsVerifyOrganization,
)


@extend_schema_view(
    list=extend_schema(summary="Список складов", description="Возвращает активные склады организации текущего пользователя."),
    retrieve=extend_schema(summary="Карточка склада", description="Возвращает склад по его UUID."),
    create=extend_schema(summary="Создать склад", description="Создаёт склад для текущей организации-поставщика. Доступно администратору подтверждённой организации-поставщика.", examples=[OpenApiExample("Новый склад", value={"name": "Основной склад", "address": "Москва, ул. Пример, 1"}, request_only=True)]),
    update=extend_schema(summary="Изменить склад", description="Полностью обновляет данные склада."),
    partial_update=extend_schema(summary="Изменить склад частично", description="Обновляет переданные поля склада."),
    destroy=extend_schema(summary="Архивировать склад", description="Деактивирует склад без физического удаления."),
)
@extend_schema(tags=["Склады"])
class WarehouseViewSet(ModelViewSet):
    queryset = Warehouse.objects.all()
    permission_classes = [
        permissions.IsAuthenticated,
        IsSupplierAdminOwner,
        IsVerifyOrganization,
    ]
    serializer_class = WarehouseListSerializer
    filterset_class = WarehouseFilter
    pagination_class = ProductNumberPagination

    lookup_field = "external_id"

    def get_queryset(self):
        queryset = self.queryset.filter(is_active=True)
        user = self.request.user

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
