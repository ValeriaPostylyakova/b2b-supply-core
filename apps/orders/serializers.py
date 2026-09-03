import django_filters
from rest_framework import serializers

from apps.accounts.models import Organization
from apps.accounts.serializers import OrganizationShortSerializer
from apps.catalog.api.serializers.product import ProductStockSerializer
from apps.catalog.api.serializers.warehouse import WarehouseStockSerializer
from apps.catalog.models.product import Product
from apps.catalog.models.warehouse import Warehouse
from apps.orders.models import FileDocument, Order, OrderItem
from config.storages import PrivateMediaStorage


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


class OrderFilter(django_filters.rest_framework.FilterSet):
    min_total = django_filters.NumberFilter(
        field_name="total_amount", lookup_expr="gte"
    )
    max_total = django_filters.NumberFilter(
        field_name="total_amount", lookup_expr="lte"
    )

    created_from = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_to = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )

    ordering = django_filters.OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("total_amount", "total_amount"),
        )
    )

    class Meta:
        model = Order
        fields = ["status"]


class OrderReportsSerializer(serializers.Serializer):
    orders_count = serializers.IntegerField()
    orders_total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    max_order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class FileDocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = FileDocument
        fields = [
            "id",
            "document_type",
            "storage_key",
            "original_name",
            "content_type",
            "size",
            "download_url",
        ]

    def get_download_url(self, obj):
        storage = PrivateMediaStorage()

        from urllib.parse import quote

        filename = quote(obj.original_name or "document.pdf")
        content_disposition = f"attachment; filename*=UTF-8''{filename}"

        return storage.url(
            obj.storage_key,
            parameters={"ResponseContentDisposition": content_disposition},
        )
