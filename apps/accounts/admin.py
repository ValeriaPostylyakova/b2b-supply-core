from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "role",
        "organization",
        "is_staff",
    )

    list_filter = ("role", "is_staff", "is_superuser", "is_active", "organization")

    search_fields = ("email", "username", "first_name", "last_name")

    # Сортировка по умолчанию
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "email", "avatar")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Business Context"),
            {
                "fields": ("role", "organization", "external_id"),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            _("Business Context"),
            {
                "fields": ("email", "role", "organization", "first_name", "last_name"),
            },
        ),
    )

    readonly_fields = ("external_id",)
