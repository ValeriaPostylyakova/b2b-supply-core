from django.db import models

from apps.catalog.managers.stock import StockQuerySet


class Stock(models.Model):
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    warehouse = models.ForeignKey(
        "catalog.Warehouse",
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)

    objects = StockQuerySet().as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"],
                name="unique_product_warehouse_stock",
            )
        ]

    def __str__(self):
        return f"{self.product.name} в {self.warehouse.name}: {self.quantity}"

    @property
    def supplier(self):
        return self.warehouse.supplier if self.warehouse else None
