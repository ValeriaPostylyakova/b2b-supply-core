from rest_framework import serializers

from apps.accounts.models import Organization
from apps.accounts.serializers import OrganizationShortSerializer
from apps.catalog.models import Product, Warehouse
from apps.catalog.serializers import ProductStockSerializer, WarehouseStockSerializer
from apps.orders.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductStockSerializer(read_only=True)
    warehouse = WarehouseStockSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "warehouse",
            "quantity",
            "unit_price",
            "line_total",
        ]

        read_only_fields = ["id"]


class OrderListSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    buyer = OrganizationShortSerializer(read_only=True)
    supplier = OrganizationShortSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "buyer",
            "supplier",
            "items_count",
            "total_amount",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "items_count",
            "total_amount",
            "created_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if not request or not request.user:
            raise serializers.ValidationError("Ошибка контекста запроса")

        if request.method == "GET":
            user = request.user
            if user.is_buyer:
                self.fields.pop("buyer", None)
            elif user.is_supplier:
                self.fields.pop("supplier", None)


class OrderDetailSerializer(OrderListSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + ["updated_at", "items"]
        read_only_fields = OrderListSerializer.Meta.read_only_fields + ["updated_at"]


class OrderItemCreateSerializer(serializers.Serializer):
    product = serializers.SlugRelatedField(
        slug_field="external_id", queryset=Product.objects.all()
    )
    warehouse = serializers.SlugRelatedField(
        slug_field="external_id", queryset=Warehouse.objects.all()
    )
    quantity = serializers.IntegerField()

    def validate_quantity(self, quantity):
        if quantity <= 0:
            raise serializers.ValidationError("Количество товара должно быть больше 0")
        return quantity


class OrderCreateSerializer(serializers.Serializer):
    supplier = serializers.SlugRelatedField(
        slug_field="external_id", queryset=Organization.objects.filter(type="SUPPLIER")
    )
    items = OrderItemCreateSerializer(required=True, many=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError(
                "Список товаров в заказе не может быть пустым"
            )
        return items

    def validate(self, attrs):
        supplier = attrs.get("supplier")
        items = attrs.get("items", [])

        for item in items:
            product = item["product"]
            warehouse = item["warehouse"]

            if product.supplier_id != supplier.id:
                raise serializers.ValidationError(
                    f"{product} не принадлежит {supplier}"
                )

            if warehouse.supplier_id != supplier.id:
                raise serializers.ValidationError(
                    f"{warehouse} не принадлежит {supplier}"
                )
        return attrs
