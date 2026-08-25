import uuid

from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models


class Product(models.Model):
    class UnitChoices(models.TextChoices):
        PIECE = 'pc', 'шт.'
        KILOGRAM = 'kg', 'кг.'
        LITER = 'l', 'л.'

    external_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    sku = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    unit = models.CharField(
        max_length=10,
        choices=UnitChoices.choices,
        default=UnitChoices.PIECE,
        verbose_name="Единица измерения"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    supplier = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        limit_choices_to={'type': "SUPPLIER"},
        related_name="products",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sku", "supplier"],
                name="unique_sku_per_supplier"
            )
        ]
        indexes = [
            models.Index(fields=["sku"], name="idx_product_sku"),
            models.Index(fields=["price"], name="idx_product_price"),
            models.Index(fields=["is_active", "price"], name="idx_product_active_price"),
            GinIndex(
                OpClass("name", name="gin_trgm_ops"),
                name="product_name_trgm_idx",
            ),
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"

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
        "accounts.Organization",
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


class Stock(models.Model):
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"],
                name="unique_product_warehouse_stock",
            )
        ]

    def __str__(self):
        return f"{self.product.name} в {self.warehouse.name}: {self.quantity}"

