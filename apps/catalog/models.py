import uuid

from django.contrib.postgres.indexes import GinIndex
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
    sku = models.CharField(max_length=100, unique=True)
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
        indexes = [
            models.Index(fields=['price'], name='idx_product_price'),
            models.Index(fields=['is_active', '-price'], name='product_active_price_idx'),
            GinIndex(fields=['name'], opclasses=['gin_trgm_ops'], name='product_name_trgm_idx'),
            GinIndex(fields=['description'], opclasses=['gin_trgm_ops'], name='product_desc_trgm_idx'),
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"

