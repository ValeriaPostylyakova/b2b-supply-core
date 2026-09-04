from django.db import models


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
