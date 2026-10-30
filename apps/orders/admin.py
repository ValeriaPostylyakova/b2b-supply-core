from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.orders.models import FileDocument, Order, OrderItem, Reservation


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ("product", "warehouse")
    readonly_fields = ("line_total",)


class FileDocumentInline(admin.TabularInline):
    model = FileDocument
    extra = 0
    readonly_fields = ("storage_key", "size", "content_type", "created_at")


class ReservationInline(admin.TabularInline):
    model = Reservation
    extra = 0
    raw_id_fields = ("stock",)
    readonly_fields = ("created_at",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "external_id",
        "buyer",
        "supplier",
        "status",
        "items_count",
        "total_amount",
        "created_at",
    )

    list_editable = ("status",)

    list_filter = ("status", "created_at", "buyer", "supplier")

    search_fields = ("id", "external_id")

    ordering = ("-created_at",)

    readonly_fields = (
        "external_id",
        "items_count",
        "total_amount",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (None, {"fields": ("status", "external_id")}),
        (
            _("Контрагенты"),
            {"fields": ("buyer", "supplier")},
        ),
        (
            _("Статистика стоимости"),
            {"fields": ("items_count", "total_amount")},
        ),
        (
            _("Временные метки"),
            {"fields": ("created_at", "updated_at")},
        ),
    )

    inlines = [OrderItemInline, FileDocumentInline, ReservationInline]


@admin.register(FileDocument)
class FileDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "original_name",
        "order",
        "document_type",
        "content_type",
        "size",
        "created_at",
    )
    list_filter = ("document_type", "content_type", "created_at")
    search_fields = ("original_name", "storage_key", "order__id")
    raw_id_fields = ("order",)
    ordering = ("-created_at",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "stock",
        "quantity",
        "status",
        "created_at",
        "expires_at",
    )
    list_filter = ("status", "created_at", "expires_at")
    search_fields = ("order__id", "stock__id")
    raw_id_fields = ("order", "stock")
    ordering = ("-created_at",)
