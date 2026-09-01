import os
from decimal import Decimal

import django_filters
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db.models import Q
from rest_framework import serializers

from apps.accounts.serializers import OrganizationShortSerializer
from apps.catalog.models import PriceListImport, Product, Stock, Warehouse

User = get_user_model()


class RoleFieldsMixin:
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        if not request or not request.user:
            return data

        user = request.user

        supplier_fields = getattr(self, "supplier_fields", set())
        buyer_fields = getattr(self, "buyer_fields", set())

        all_role_fields = supplier_fields | buyer_fields
        allowed_fields = supplier_fields if user.is_supplier else buyer_fields

        fields_to_remove = all_role_fields - allowed_fields
        for field in fields_to_remove:
            data.pop(field, None)

        return data


class WarehouseListSerializer(RoleFieldsMixin, serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    products_count = serializers.IntegerField(read_only=True)
    supplier = serializers.SlugRelatedField(slug_field="name", read_only=True)

    supplier_fields = {"products_count", "created_at", "updated_at", "is_active"}
    buyer_fields = {"supplier"}

    class Meta:
        model = Warehouse
        fields = [
            "id",
            "name",
            "address",
            "is_active",
            "created_at",
            "updated_at",
            "products_count",
            "supplier",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class WarehouseCreateUpdateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    supplier = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Warehouse
        fields = [
            "id",
            "name",
            "address",
            "supplier",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = WarehouseListSerializer.Meta.read_only_fields + ["supplier"]

    def validate(self, attrs):
        if not self.instance:
            if "is_active" in attrs:
                raise serializers.ValidationError(
                    "Поле is_active не может быть указано при создании склада"
                )
        return attrs


class WarehouseFilter(django_filters.rest_framework.FilterSet):
    search = django_filters.CharFilter(method="filter_search", label="Поиск")
    ordering = django_filters.OrderingFilter(
        fields=[
            "name",
            "created_at",
        ],
        field_labels={"name": "Название", "created_at": "Дата создания"},
    )

    class Meta:
        model = Warehouse
        fields = ["search", "ordering", "is_active"]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(supplier__name__icontains=value)
        ).distinct()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.request
        if not request or not request.user:
            return

        user = request.user
        if not user.is_supplier:
            self.filters.pop("is_active", None)


class ProductListSerializer(RoleFieldsMixin, serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    reserved_quantity = serializers.IntegerField(read_only=True)

    supplier_fields = {"available_quantity", "quantity", "reserved_quantity"}
    buyer_fields = {"available_quantity"}

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "price",
            "description",
            "is_active",
            "available_quantity",
            "quantity",
            "reserved_quantity",
        ]


class ProductWarehouseListSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="warehouse.external_id", read_only=True)
    name = serializers.CharField(source="warehouse.name", read_only=True)
    address = serializers.CharField(source="warehouse.address", read_only=True)
    supplier = OrganizationShortSerializer(source="warehouse.supplier", read_only=True)
    is_active = serializers.BooleanField(source="warehouse.is_active", read_only=True)

    quantity = serializers.IntegerField(read_only=True)
    reserved_quantity = serializers.IntegerField(read_only=True)
    available_quantity = serializers.SerializerMethodField()

    supplier_fields = {"available_quantity", "quantity", "reserved_quantity"}
    buyer_fields = {"supplier", "available_quantity"}

    class Meta:
        model = Stock
        fields = [
            "id",
            "name",
            "address",
            "is_active",
            "supplier",
            "quantity",
            "reserved_quantity",
            "available_quantity",
        ]

    def get_available_quantity(self, obj):
        return max(0, obj.quantity - obj.reserved_quantity)


class ProductListDetailSerializer(ProductListSerializer):
    warehouses = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = list(ProductListSerializer.Meta.fields) + ["warehouses"]

    def get_warehouses(self, obj):
        stocks = obj.stocks.all()
        return [
            ProductWarehouseListSerializer(stock, context=self.context).data
            for stock in stocks
        ]


class ProductFilter(django_filters.rest_framework.FilterSet):
    search = django_filters.CharFilter(method="filter_search", label="Поиск")

    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    available = django_filters.BooleanFilter(field_name="is_active", label="Доступен")

    ordering = django_filters.OrderingFilter(
        fields=["price", "created_at", "name"],
        field_labels={
            "price": "Цена",
            "created_at": "Дата создания",
            "name": "Название",
        },
    )

    class Meta:
        model = Product
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(sku__icontains=value)
        ).distinct()


class ProductCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    supplier = serializers.SlugRelatedField(slug_field="name", read_only=True)
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(
                0.01, message="Цена товара не может быть меньше или равна 0."
            )
        ],
    )

    class Meta:
        model = Product
        fields = ["id", "sku", "name", "price", "description", "supplier"]


class ProductUpdateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(
                0.01, message="Цена товара не может быть меньше или равна 0."
            )
        ],
    )

    class Meta:
        model = Product
        fields = ["id", "name", "price", "description"]


class ProductStockSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "sku", "name"]


class WarehouseStockSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    class Meta:
        model = Warehouse
        fields = ["id", "name", "address"]


class StockListSerializer(serializers.ModelSerializer):
    product = ProductStockSerializer(read_only=True)
    warehouse = WarehouseStockSerializer(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Stock
        fields = [
            "id",
            "product",
            "warehouse",
            "quantity",
            "reserved_quantity",
            "available_quantity",
        ]
        read_only_fields = ["id", "available_quantity"]


class StockUpdateSerializer(serializers.ModelSerializer):
    available_quantity = serializers.IntegerField()

    class Meta:
        model = Stock
        fields = ["id", "quantity", "reserved_quantity", "available_quantity"]
        read_only_fields = ["id", "reserved_quantity", "available_quantity"]

    def validate_quantity(self, value):
        if value == self.instance.quantity:
            raise serializers.ValidationError(
                "Новое количество должно отличаться от текущего."
            )
        return value


class StockReportsSerializer(serializers.Serializer):
    products_count = serializers.IntegerField(read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    total_reserved = serializers.IntegerField(read_only=True)
    total_available = serializers.IntegerField(read_only=True)


class ProductImportRowSerializer(serializers.Serializer):
    sku = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )
    name = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )
    warehouse = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    quantity = serializers.IntegerField(min_value=0)


class PriceListImportStatusSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id")

    class Meta:
        model = PriceListImport
        fields = [
            "id",
            "status",
            "total_rows",
            "success_rows",
            "error_rows",
        ]


class PriceListImportCreateSerializer(serializers.Serializer):
    storage_key = serializers.CharField(max_length=512)
    original_name = serializers.CharField(max_length=255)


class PriceListPresignedUrlRequestSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)

    def validate_file_name(self, value):
        _, ext = os.path.splitext(value)
        ext = ext.lower()
        allowed_extensions = [".xlsx", ".xls"]

        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                "Недопустимый формат файла. Разрешены только файлы Excel (.xlsx, .xls)."
            )

        return value
