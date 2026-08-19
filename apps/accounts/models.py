import uuid
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models


class Organization(models.Model):
    class Types(models.TextChoices):
        SUPPLIER = 'SUPPLIER', 'Поставщик'
        BUYER = 'BUYER', 'Покупатель'

    external_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(
        max_length=150,
        choices=Types.choices,
        verbose_name='Тип организации'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Roles(models.TextChoices):
        SUPPLIER = 'SUPPLIER', 'Поставщик'
        BUYER = 'BUYER', 'Покупатель'
        ADMIN = 'admin', 'Администратор'

    username = None
    external_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(
        max_length=150,
        choices=Roles.choices,
        verbose_name='Роль пользователя'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="users",
    )
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

