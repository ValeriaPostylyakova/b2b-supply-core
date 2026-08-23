import django_filters
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers

from apps.accounts.models import Organization
from apps.catalog.models import Product, Warehouse

User = get_user_model()

class WarehouseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'address', ]

class WarehouseListBuyerSerializer(WarehouseListSerializer):
    available_quantity = serializers.IntegerField(read_only=True)
    class Meta:
        model = Warehouse
        fields = WarehouseListSerializer.Meta.fields + ['available_quantity']

class WarehouseListSupplierSerializer(WarehouseListBuyerSerializer):
    quantity = serializers.IntegerField(read_only=True)
    reserved_quantity = serializers.IntegerField(read_only=True)
    class Meta:
        model = Warehouse
        fields = WarehouseListBuyerSerializer.Meta.fields + ['quantity', 'reserved_quantity']


class ProductListSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='external_id', read_only=True)
    supplier = serializers.SlugRelatedField(slug_field='name', read_only=True)
    class Meta:
        model = Product
        fields = ['id', 'sku', 'name', 'price', 'description', 'unit', 'is_active']


class ProductListBuyerSerializer(ProductListSerializer):
    supplier = serializers.SlugRelatedField(slug_field='name', read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = ProductListSerializer.Meta.fields + ['supplier', 'available_quantity']

class ProductListSupplierSerializer(ProductListSerializer):
    available_quantity = serializers.IntegerField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    reserved_quantity = serializers.IntegerField(read_only=True)
    class Meta:
        model = Product
        fields = ProductListSerializer.Meta.fields + ['available_quantity', 'quantity', 'reserved_quantity']

class ProductListDetailBuyerSerializer(ProductListSerializer):
    warehouses = WarehouseListBuyerSerializer(many=True, read_only=True)
    class Meta:
        model = Product
        fields = ProductListSerializer.Meta.fields + ['warehouses']

class ProductListDetailSupplierSerializer(ProductListSupplierSerializer):
    warehouses = WarehouseListSupplierSerializer(many=True, read_only=True)
    class Meta:
        model = Product
        fields = ProductListSupplierSerializer.Meta.fields + ['warehouses']

class ProductListDetailSerializer(ProductListSerializer):
    warehouses = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ProductListSerializer.Meta.fields + ["warehouses"]

    def get_warehouses(self, obj):
        request = self.context.get('request')
        if request.user.role == User.Roles.startswith('SUPPLIER_'):
            return WarehouseListSupplierSerializer(obj.warehouses, many=True, context=self.context).data
        return WarehouseListBuyerSerializer(obj.warehouses, many=True, context=self.context).data





class ProductFilter(django_filters.rest_framework.FilterSet):
    search = django_filters.CharFilter(method='filter_search', label='Поиск')

    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    available = django_filters.BooleanFilter(field_name='is_active', label='Доступен')

    ordering = django_filters.OrderingFilter(
        fields=(
            ("price", "price"),
            ("created_at", "created_at"),
            ("name", "name"),
        )
    )

    class Meta:
        model = Product
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(sku__icontains=value)).distinct()
