from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import PriceListImport, Product, Stock, Warehouse


@admin.register(PriceListImport)
class PriceListImportAdmin(admin.ModelAdmin):
    list_display = (
        "external_id",
        "supplier",
        "original_name",
        "status",
        "total_rows",
        "success_rows",
        "error_rows",
        "created_at",
    )

    list_filter = ("status", "supplier", "created_at")

    search_fields = ("original_name", "external_id", "storage_key")

    ordering = ("-created_at",)

    readonly_fields = (
        "external_id",
        "supplier",
        "original_name",
        "storage_key",
        "status",
        "total_rows",
        "success_rows",
        "error_rows",
        "created_at",
    )


class StockInline(admin.TabularInline):
    model = Stock
    extra = 1
    raw_id_fields = ("product", "warehouse")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "name",
        "supplier",
        "price",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "supplier", "created_at")
    search_fields = ("sku", "name", "external_id")
    ordering = ("sku",)
    readonly_fields = ("external_id", "created_at", "updated_at")

    list_editable = ("is_active", "price")

    inlines = [StockInline]


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "supplier",
        "address",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "supplier")
    search_fields = ("name", "address", "external_id")
    ordering = ("-created_at",)
    readonly_fields = ("external_id", "created_at", "updated_at")
    list_editable = ("is_active",)

    inlines = [StockInline]


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "warehouse",
        "quantity",
        "reserved_quantity",
        "get_supplier",
    )
    list_filter = ("warehouse__supplier", "warehouse")
    search_fields = ("product__name", "product__sku", "warehouse__name")

    raw_id_fields = ("product", "warehouse")

    @admin.display(description=_("Supplier"))
    def get_supplier(self, obj):
        return obj.supplier
