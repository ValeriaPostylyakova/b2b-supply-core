import uuid

from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models


class Product(models.Model):
    external_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    sku = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    supplier = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        limit_choices_to={"type": "SUPPLIER"},
        related_name="products",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sku", "supplier"], name="unique_sku_per_supplier"
            )
        ]
        indexes = [
            models.Index(fields=["sku"], name="idx_product_sku"),
            models.Index(fields=["price"], name="idx_product_price"),
            models.Index(
                fields=["is_active", "price"], name="idx_product_active_price"
            ),
            GinIndex(
                OpClass("name", name="gin_trgm_ops"),
                name="product_name_trgm_idx",
            ),
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"
