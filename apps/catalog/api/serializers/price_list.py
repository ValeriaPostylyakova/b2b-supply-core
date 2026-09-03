import os
from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models.price_list import PriceListImport


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
