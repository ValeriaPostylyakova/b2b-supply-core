from django.db import models


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Создан (ожидает действия)"),
        ("succeeded", "Успешно оплачен"),
        ("canceled", "Отклонен/Истек"),
    ]

    PROVIDER_CHOICES = [
        ("yookassa", "ЮKassa"),
    ]

    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="payments"
    )

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    external_payment_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )

    raw_response = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
