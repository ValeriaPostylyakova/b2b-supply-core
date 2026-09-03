from rest_framework import serializers

from apps.catalog.api.serializers.product import ProductStockSerializer
from apps.catalog.api.serializers.warehouse import WarehouseStockSerializer
from apps.catalog.models.stock import Stock


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
