from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.orders.models import Order, OrderItem, Reservation


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ("product", "warehouse")
    readonly_fields = ("line_total",)



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

    inlines = [OrderItemInline, ReservationInline]

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
