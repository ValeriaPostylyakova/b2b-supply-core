from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.organizations.models import Organization, OrganizationInvite


class OrganizationInviteInline(admin.TabularInline):
    model = OrganizationInvite
    extra = 0
    readonly_fields = (
        "external_id",
        "token_hash",
        "created_at",
        "accepted_at",
        "expires_at",
    )
    fields = ("external_id", "email", "role", "status", "expires_at", "accepted_at")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "type",
        "inn",
        "kpp",
        "verification_status",
        "created_at",
    )

    list_editable = ("verification_status",)

    list_filter = ("type", "verification_status", "created_at")

    search_fields = ("name", "inn", "kpp", "external_id")

    ordering = ("-created_at",)

    readonly_fields = ("external_id", "created_at")

    fieldsets = (
        (None, {"fields": ("name", "type", "external_id")}),
        (
            _("Юридические данные"),
            {"fields": ("inn", "kpp", "legal_address")},
        ),
        (
            _("Бизнес статус"),
            {"fields": ("verification_status", "description")},
        ),
        (
            _("Служебная информация"),
            {"fields": ("created_at",)},
        ),
    )

    inlines = [OrganizationInviteInline]


@admin.register(OrganizationInvite)
class OrganizationInviteAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "organization",
        "role",
        "status",
        "created_at",
        "expires_at",
        "accepted_at",
    )
    list_filter = ("status", "role", "created_at")
    search_fields = ("email", "organization__name", "external_id")

    raw_id_fields = ("organization",)

    ordering = ("-created_at",)
    readonly_fields = ("external_id", "token_hash", "created_at", "accepted_at")
