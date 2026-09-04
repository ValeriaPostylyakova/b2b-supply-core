import uuid

from django.db import models


class Organization(models.Model):
    class Types(models.TextChoices):
        SUPPLIER = "SUPPLIER", "Поставщик"
        BUYER = "BUYER", "Покупатель"

    external_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(
        max_length=150, choices=Types.choices, verbose_name="Тип организации"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    objects: models.Manager["Organization"]

    def __str__(self):
        return self.name
