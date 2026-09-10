import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit

from apps.accounts.services.user_avatar_upload_path import AccountService


class User(AbstractUser):
    class Roles(models.TextChoices):
        SUPPLIER_ADMIN = "SUPPLIER_ADMIN", "Администратор организации-поставщика"
        SUPPLIER_MANAGER = "SUPPLIER_MANAGER", "Менеджер поставщика"
        WAREHOUSE_MANAGER = "WAREHOUSE_MANAGER", "Сотрудник склада"
        BUYER_ADMIN = "BUYER_ADMIN", "Администратор организации-покупателя"
        BUYER_MANAGER = "BUYER_MANAGER", "Менеджер по закупкам"

    external_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=150, choices=Roles.choices, verbose_name="Роль пользователя"
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )

    username = models.CharField(unique=True)
    avatar = ProcessedImageField(
        upload_to=AccountService.user_avatar_upload_path,
        processors=[ResizeToFit(500, 500)],
        format="JPEG",
        options={"quality": 85},
    )
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "username"]

    def __str__(self):
        return self.email

    @property
    def is_supplier(self):
        return bool(self.role.startswith("SUPPLIER_"))

    @property
    def is_buyer(self):
        return bool(self.role.startswith("BUYER_"))

    @property
    def is_warehouse(self):
        return bool(self.role.startswith("WAREHOUSE_"))

    @property
    def has_organization(self):
        return bool(self.organization_id)
