from django.core.validators import MinValueValidator
from rest_framework import serializers

from apps.catalog.models.product import Product
from apps.catalog.models.stock import Stock
from apps.common.mixins.role_fields_mixin import RoleFieldsMixin
from apps.organizations.api.serializers import OrganizationShortSerializer


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
