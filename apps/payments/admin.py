from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.payments.models import (
    Payment,
)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "provider",
        "amount",
        "status",
        "external_payment_id",
        "created_at",
    )

    list_editable = ("status",)

    list_filter = ("status", "provider", "created_at", "updated_at")

    search_fields = ("id", "order__id", "external_payment_id")

    ordering = ("-created_at",)

    raw_id_fields = ("order",)

    readonly_fields = (
        "provider",
        "amount",
        "external_payment_id",
        "raw_response",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            None,
            {"fields": ("status", "order")},
        ),
        (
            _("Детали транзакции"),
            {"fields": ("provider", "amount", "external_payment_id")},
        ),
        (
            _("Техническая информация (API Лог)"),
            {
                "classes": ("collapse",),
                "fields": ("raw_response",),
            },
        ),
        (
            _("Временные метки"),
            {"fields": ("created_at", "updated_at")},
        ),
    )
