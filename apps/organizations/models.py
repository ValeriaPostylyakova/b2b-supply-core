import uuid

from django.db import models


class Organization(models.Model):
    class Types(models.TextChoices):
        SUPPLIER = "SUPPLIER", "Поставщик"
        BUYER = "BUYER", "Покупатель"

    external_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "На рассмотрении"
        VERIFIED = "VERIFIED", "Подтверждено"
        REJECTED = "REJECTED", "Отклонено"

    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(
        max_length=150, choices=Types.choices, verbose_name="Тип организации"
    )

    inn = models.CharField(max_length=12, unique=True)
    kpp = models.CharField(max_length=9, unique=True)
    legal_address = models.TextField()
    description = models.TextField(blank=True, null=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.type})"


class OrganizationInvite(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "На рассмотрении"
        ACCEPTED = "ACCEPTED", "Принято"
        EXPIRED = "EXPIRED", "Истекло"
        REVOKED = "REVOKED", "Отозвано"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="invites",
    )
    email = models.EmailField()
    role = models.CharField(max_length=50)
    token_hash = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    invited_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_invites",
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
