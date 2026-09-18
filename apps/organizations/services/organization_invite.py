import hashlib
import secrets

from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.organizations.models.organization_invite import OrganizationInvite
from apps.organizations.tasks.organization_invite.send_invite_email import (
    send_invite_email_task,
)
from apps.organizations.tasks.organization_invite.send_welcome_team_email import (
    send_welcome_team_email_task,
)

User = get_user_model()


class OrganizationInviteService:
    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    @transaction.atomic
    def create_invite(validated_data, organization):
        email = validated_data["email"]
        role = validated_data["role"]

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
            defaults={
                "organization": invite.organization,
                "username": invite.email,
                "role": invite.role,
                "is_active": False,
            },
        )

        if not created:
            user.organization = invite.organization
            user.role = invite.role
            user.save(update_fields=["organization", "role"])

        invite.status = OrganizationInvite.Status.ACCEPTED
        invite.accepted_at = timezone.now()
        invite.save(update_fields=["status", "accepted_at"])

        return user, created

    @staticmethod
    def register_invited_user(registration_token, reg_salt, **user_data):
        try:
            data = signing.loads(registration_token, salt=reg_salt, max_age=900)
            user_id = data.get("user_id")
        except signing.SignatureExpired:
            raise ValidationError(
                {
                    "registration_token": "Срок действия токена регистрации истек. Запросите приглашение заново."
                }
            )
        except signing.BadSignature:
            raise ValidationError(
                {"registration_token": "Недействительный токен регистрации."}
            )

        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(id=user_id)
                password = user_data.pop("password", None)

                for field, value in user_data.items():
                    setattr(user, field, value)

                if password:
                    user.set_password(password)

                user.is_active = True
                user.save()

                send_welcome_team_email_task.delay_on_commit(user.id, user.organization_id)

        except User.DoesNotExist:
            raise ValidationError({"registration_token": "Пользователь не найден."})

        return user
