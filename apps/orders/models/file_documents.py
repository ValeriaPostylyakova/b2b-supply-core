from django.db import models


class DocumentTypeChoices(models.TextChoices):
    INVOICE = "invoice", "Invoice"


class FileDocument(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentTypeChoices.choices,
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
                condition=models.Q(document_type=DocumentTypeChoices.INVOICE),
                name="unique_invoice_per_order",
            )
        ]

    def __str__(self):
        return (
            f"{self.document_type} для заказа №{self.order_id} ({self.original_name})"
        )
