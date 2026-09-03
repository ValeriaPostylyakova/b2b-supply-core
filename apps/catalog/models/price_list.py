import uuid

from django.db import models


class PriceListImport(models.Model):
    external_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

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
        "accounts.Organization",
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
    success_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
