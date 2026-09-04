import uuid

from django.core.validators import MinValueValidator
from django.db import models

from apps.orders.selectors.order import OrderQuerySet


class Order(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = "DRAFT", "Черновик"
        RESERVED = "RESERVED", "Зарезервирован"
        CONFIRMED = "CONFIRMED", "Подтвержден"
        CANCELLED = "CANCELLED", "Отменен"
        COMPLETED = "COMPLETED", "Выполнен"

    external_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    buyer = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="buyer_orders",
    )
    supplier = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="supplier_orders",
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
        db_index=True,
    )
    items_count = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00)],
        verbose_name="Итоговая сумма",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrderQuerySet().as_manager()

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["status", "created_at"], name="order_status_created_idx"
            ),
            models.Index(
                fields=["status", "total_amount"], name="order_status_total_idx"
            ),
            models.Index(fields=["created_at"], name="order_created_at_idx"),
        ]

    def __str__(self):
        return f"Заказ №{self.id} от {self.created_at.strftime('%d.%m.%Y')}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    warehouse = models.ForeignKey(
        "catalog.Warehouse",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} ({self.quantity} x {self.unit_price})"
