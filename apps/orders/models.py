import uuid

from django.core.validators import MinValueValidator
from django.db import models


class Order(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = "DRAFT", "Черновик"
        RESERVED = "RESERVED", "Зарезервирован"
        CONFIRMED = "CONFIRMED", "Подтвержден"
        CANCELLED = "CANCELLED", "Отменен"
        COMPLETED = "COMPLETED", "Выполнен"

    external_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    buyer = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.PROTECT,
        related_name="buyer_orders",
    )
    supplier = models.ForeignKey(
        "accounts.Organization",
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

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]

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


class Reservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Активна"
        RELEASED = "RELEASED", "Снята (Освобождена)"
        CONSUMED = "CONSUMED", "Выкуплена (Потрачена)"
        EXPIRED = "EXPIRED", "Просрочена"

    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="reservations"
    )
    stock = models.ForeignKey(
        "catalog.Stock", on_delete=models.PROTECT, related_name="reservations"
    )
    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()


class DocumentTypeСhoices(models.TextChoices):
    INVOICE = "invoice", "Invoice"


class FileDocument(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentTypeСhoices.choices,
    )
    storage_key = models.CharField(max_length=500)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Документ заказа"
        verbose_name_plural = "Документы заказов"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["order", "document_type"],
                condition=models.Q(document_type=DocumentTypeСhoices.INVOICE),
                name="unique_invoice_per_order",
            )
        ]

    def __str__(self):
        return (
            f"{self.document_type} для заказа №{self.order_id} ({self.original_name})"
        )
