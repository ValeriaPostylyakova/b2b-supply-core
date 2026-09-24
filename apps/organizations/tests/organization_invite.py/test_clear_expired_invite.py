from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.organizations.models import OrganizationInvite
from apps.organizations.models.organization import (
    Organization,
)
from apps.organizations.tasks.organization_invite.clear_expired_invite import (
    clear_expired_invite_task,
)


@pytest.mark.django_db
class TestClearExpiredInviteTask:
    @pytest.fixture(autouse=True)
    def setup_organization(self):
        """Фикстура, которая автоматически создает организацию для каждого теста."""
        self.org = Organization.objects.create(
            name="Тестовая организация", type="SUPPLIER"
        )

    @freeze_time("2026-09-24 03:00:00")
    def test_clear_expired_invites_success(self):
        now = timezone.now()

        expired_invite = OrganizationInvite.objects.create(
            organization=self.org,
            token_hash="token_1",
            status=OrganizationInvite.Status.PENDING,
            expires_at=now - timedelta(minutes=5),
        )
        future_invite = OrganizationInvite.objects.create(
            organization=self.org,
            token_hash="token_2",
            status=OrganizationInvite.Status.PENDING,
            expires_at=now + timedelta(hours=1),
        )
        other_status_invite = OrganizationInvite.objects.create(
            organization=self.org,
            token_hash="token_3",
            status=OrganizationInvite.Status.ACCEPTED,
            expires_at=now - timedelta(minutes=5),
        )

        result = clear_expired_invite_task()

        assert result == {"processed": 1}

        expired_invite.refresh_from_db()
        future_invite.refresh_from_db()
        other_status_invite.refresh_from_db()

        assert expired_invite.status == OrganizationInvite.Status.EXPIRED
        assert future_invite.status == OrganizationInvite.Status.PENDING
        assert other_status_invite.status == OrganizationInvite.Status.ACCEPTED

    @freeze_time("2026-09-24 03:00:00")
    def test_clear_expired_invites_trigger_next_batch(self):
        now = timezone.now()
        batch_size = 200

        invites = [
            OrganizationInvite(
                organization=self.org,
                token_hash=f"bulk_token_{i}",
                status=OrganizationInvite.Status.PENDING,
                expires_at=now - timedelta(minutes=1),
            )
            for i in range(batch_size)
        ]
        OrganizationInvite.objects.bulk_create(invites)

        with patch.object(clear_expired_invite_task, "apply_async") as mock_apply_async:
            result = clear_expired_invite_task()

            assert result == {"processed": batch_size}
            mock_apply_async.assert_called_once_with(countdown=0)

    @freeze_time("2026-09-24 03:00:00")
    @patch(
        "apps.organizations.models.organization_invite.OrganizationInvite.objects.select_for_update"
    )
    def test_clear_expired_invites_retry_on_exception(self, mock_select_for_update):
        now = timezone.now()

        OrganizationInvite.objects.create(
            organization=self.org,
            token_hash="token_retry",
            status=OrganizationInvite.Status.PENDING,
            expires_at=now - timedelta(minutes=1),
        )

        mock_select_for_update.side_effect = Exception("Database deadlock")

        clear_expired_invite_task.retry = MagicMock(
            side_effect=RuntimeError("Retry called")
        )

        with pytest.raises(RuntimeError, match="Retry called"):
            clear_expired_invite_task()

        clear_expired_invite_task.retry.assert_called_once()

        kwargs = clear_expired_invite_task.retry.call_args[1]
        assert "exc" in kwargs
        assert str(kwargs["exc"]) == "Database deadlock"
