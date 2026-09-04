import uuid

from django.contrib.postgres.indexes import GinIndex
from django.db import models


class Warehouse(models.Model):
    external_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    name = models.CharField(max_length=150, unique=True)
    address = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    supplier = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        limit_choices_to={"type": "SUPPLIER"},
        related_name="warehouses",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "supplier"], name="unique_name_per_supplier"
            )
        ]
        indexes = [
            GinIndex(
                name="warehouse_name_trgm_idx",
                fields=["name"],
                opclasses=["gin_trgm_ops"],
            ),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.address}"
