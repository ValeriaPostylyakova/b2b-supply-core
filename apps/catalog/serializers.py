import django_filters
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db.models import Q
from mypy.dmypy.client import request
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.catalog.models import Product, Warehouse, Stock

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

    supplier_fields = {"products_count", 'created_at', 'updated_at', 'is_active'}
    buyer_fields = {'supplier'}
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'address', 'is_active', 'created_at', 'updated_at', 'products_count', 'supplier']
        read_only_fields = ['id', 'created_at', 'updated_at']


class WarehouseCreateUpdateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    supplier = serializers.SlugRelatedField(slug_field="name", read_only=True)
    class Meta:
        model = Warehouse
        fields = ["id", "name", "address", "supplier", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "supplier", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not request.user:
            raise serializers.ValidationError("Ошибка контекста запроса")

        user = request.user
        if not self.instance:
            if "is_active" in attrs:
                raise serializers.ValidationError("Поле is_active не может быть указано при создании склада")
            attrs["supplier"] = user.organization
        return attrs

class WarehouseFilter(django_filters.rest_framework.FilterSet):
    search = django_filters.CharFilter(method='filter_search', label='Поиск')
    ordering = django_filters.OrderingFilter(
        fields=[
            "name",
            "created_at",
        ],
        field_labels={"name": "Название", "created_at": "Дата создания"},
    )

    class Meta:
        model = Warehouse
        fields = ['search', 'ordering', 'is_active']

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(supplier__name__icontains=value)).distinct()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.request
        if not request or not request.user:
            return

        user = request.user
        if not user.is_supplier:
            self.filters.pop("is_active", None)

class ProductListSerializer(RoleFieldsMixin, serializers.ModelSerializer):
    id = serializers.UUIDField(source='external_id', read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    reserved_quantity = serializers.IntegerField(read_only=True)

    supplier_fields = {"available_quantity", "quantity", "reserved_quantity"}
    buyer_fields = {"available_quantity"}

    class Meta:
        model = Product
        fields = ['id', 'sku', 'name', 'price', 'description', 'unit', 'is_active', 'available_quantity', 'quantity', 'reserved_quantity']


class ProductWarehouseListSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='warehouse.external_id', read_only=True)
    name = serializers.CharField(source='warehouse.name', read_only=True)
    address = serializers.CharField(source='warehouse.address', read_only=True)
    supplier = serializers.SlugRelatedField(slug_field="name", source='warehouse.supplier', read_only=True)
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
    search = django_filters.CharFilter(method='filter_search', label='Поиск')

    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    available = django_filters.BooleanFilter(field_name='is_active', label='Доступен')

    ordering = django_filters.OrderingFilter(
        fields=[
            'price',
            'created_at',
            'name'
        ],
        field_labels={
            'price': 'Цена',
            'created_at': 'Дата создания',
            'name': 'Название'
        }
    )

    class Meta:
        model = Product
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(sku__icontains=value)).distinct()


class ProductCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='external_id', read_only=True)
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
        fields = ['id','sku', 'name', 'price', 'description', 'supplier']

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Ошибка контекста запроса")

        current_user_organization = getattr(request.user, "organization", None)
        attrs['supplier'] = current_user_organization

        return attrs


class ProductUpdateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='external_id', read_only=True)
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
        fields = ['id', 'name', 'price', 'description']