from rest_framework import serializers

from apps.catalog.models.warehouse import Warehouse
from apps.common.mixins.role_fields_mixin import RoleFieldsMixin


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


class WarehouseStockSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    class Meta:
        model = Warehouse
        fields = ["id", "name", "address"]
