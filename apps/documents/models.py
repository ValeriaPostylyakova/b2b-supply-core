from django.db import models


class FileDocument(models.Model):
    class DocumentType(models.TextChoices):
        INVOICE = "INVOICE", "Invoice"

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
    )
    storage_key = models.CharField(max_length=500)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "file_documents"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.original_name


class PriceListImport(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        COMPLETED_WITH_ERRORS = (
            "COMPLETED_WITH_ERRORS",
            "Completed with errors",
        )

    supplier = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.PROTECT,
        related_name="price_list_imports",
    )
    original_name = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=500)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )
    total_rows = models.PositiveIntegerField(default=0)
    processed_rows = models.PositiveIntegerField(default=0)
    success_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
