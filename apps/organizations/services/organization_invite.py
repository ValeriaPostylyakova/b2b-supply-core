import hashlib
import secrets

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.organizations.models.organization_invite import OrganizationInvite
from apps.organizations.tasks.organization_invite import send_invite_email_task

User = get_user_model()


class OrganizationInviteService:
    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    @transaction.atomic
    def create_invite(email, organization, role):
        if User.objects.filter(email=email, organization=organization).exists():
            raise ValidationError(
                {"email": "Этот пользователь уже является участником организации."}
            )

        if OrganizationInvite.objects.filter(
            email=email,
            organization=organization,
            status=OrganizationInvite.Status.PENDING,
        ).exists():
            raise ValidationError(
                {"email": "У данного пользователя есть действующее приглашение."}
            )

        raw_token = secrets.token_urlsafe(32)
        token_hash = OrganizationInviteService._hash_token(raw_token)
        expires_at = timezone.now() + timezone.timedelta(days=1)

        invite = OrganizationInvite.objects.create(
            organization=organization,
            email=email,
            role=role,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        send_invite_email_task.delay_on_commit(invite_id=invite.id, raw_token=raw_token)

        return invite

    @staticmethod
    @transaction.atomic
    def accept_invite(raw_token: str):
        token_hash = OrganizationInviteService._hash_token(raw_token)

        try:
            invite = OrganizationInvite.objects.select_for_update().get(
                token_hash=token_hash
            )
        except OrganizationInvite.DoesNotExist:
            raise ValidationError(
                {"token": "Недействительный или устаревший токен приглашения."}
            )

        if invite.status != OrganizationInvite.Status.PENDING:
            raise ValidationError(
                {"token": "Недействительный или устаревший токен приглашения."}
            )

        if invite.expires_at < timezone.now():
            raise ValidationError({"token": "Срок действия этого приглашения истек."})

        user, created = User.objects.get_or_create(
            email=invite.email,
            username=invite.email,
            defaults={
                "organization": invite.organization,
                "role": invite.role,
            },
        )

        if not created:
            user.organization = invite.organization
            user.role = invite.role
            user.save(update_fields=["organization", "role"])

        invite.status = OrganizationInvite.Status.ACCEPTED
        invite.save(update_fields=["status"])

        return user, created
