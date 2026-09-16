import uuid

from django.db import models


class OrganizationInvite(models.Model):
    external_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

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

    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
