from django.db import models

class Warehouse(models.Model):
    name = models.CharField(max_length=150, unique=True)
    address = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    supplier = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        limit_choices_to={'type': 'SUPPLIER'},
        related_name='warehouses'
    )

    def __str__(self):
        return self.name


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
