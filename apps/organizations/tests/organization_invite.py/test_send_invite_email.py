from datetime import timedelta
from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from django.utils import timezone

from apps.organizations.models.organization_invite import OrganizationInvite
from apps.organizations.tasks.organization_invite.send_invite_email import (
    send_invite_email_task,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def organization(db):
    from apps.organizations.models.organization import Organization

    return Organization.objects.create(name="Acme Inc")


@pytest.fixture
def invite(organization):
    return OrganizationInvite.objects.create(
        organization=organization,
        email="newuser@example.com",
        role="member",
        token_hash="token_hash_123",
        status=OrganizationInvite.Status.PENDING,
        expires_at=timezone.now() + timedelta(days=7),
    )


class TestSendInviteEmailTaskSuccess:
    def test_sends_email_and_returns_true(self, invite, mailoutbox):
        result = send_invite_email_task.apply(args=[invite.id, "raw-token-123"]).get()

        assert result is True
        assert len(mailoutbox) == 1

    def test_email_recipient_is_invite_email(self, invite, mailoutbox):
        send_invite_email_task.apply(args=[invite.id, "raw-token-123"])

        sent = mailoutbox[0]
        assert sent.to == [invite.email]

    def test_email_subject_contains_organization_name(self, invite, mailoutbox):
        send_invite_email_task.apply(args=[invite.id, "raw-token-123"])

        sent = mailoutbox[0]
        assert invite.organization.name in sent.subject

    def test_email_has_html_alternative(self, invite, mailoutbox):
        send_invite_email_task.apply(args=[invite.id, "raw-token-123"])

        sent = mailoutbox[0]
        assert len(sent.alternatives) == 1
        html_content, mime_type = sent.alternatives[0]
        assert mime_type == "text/html"

    def test_accept_url_contains_raw_token(self, invite, mailoutbox, settings):
        settings.FRONTEND_URL = "https://app.example.com"

        send_invite_email_task.apply(args=[invite.id, "raw-token-123"])

        sent = mailoutbox[0]
        html_body, _ = sent.alternatives[0]
        assert "raw-token-123" in html_body
        assert "https://app.example.com/invite/accept/" in html_body

    def test_plain_message_has_no_html_tags(self, invite, mailoutbox):
        send_invite_email_task.apply(args=[invite.id, "raw-token-123"])

        sent = mailoutbox[0]
        assert "<" not in sent.body and ">" not in sent.body


class TestSendInviteEmailTaskInviteNotFound:
    def test_returns_false_when_invite_does_not_exist(self, caplog):
        non_existent_id = 999999

        result = send_invite_email_task.apply(
            args=[non_existent_id, "raw-token-123"]
        ).get()

        assert result is False

    def test_logs_error_when_invite_does_not_exist(self, caplog):
        non_existent_id = 999999

        with caplog.at_level("ERROR"):
            send_invite_email_task.apply(args=[non_existent_id, "raw-token-123"])

        assert any(str(non_existent_id) in record.message for record in caplog.records)

    def test_does_not_send_email_when_invite_missing(self, mailoutbox):
        send_invite_email_task.apply(args=[999999, "raw-token-123"])

        assert len(mailoutbox) == 0


class TestSendInviteEmailTaskRetry:
    def test_retries_on_send_failure(self, invite):
        with (
            patch(
                "apps.organizations.tasks.organization_invite.send_invite_email.EmailMultiAlternatives.send",
                side_effect=Exception("SMTP connection failed"),
            ),
            pytest.raises(Retry),
        ):
            send_invite_email_task.apply(
                args=[invite.id, "raw-token-123"], throw=True
            ).get()

    def test_logs_warning_on_send_failure(self, invite, caplog):
        with (
            patch(
                "apps.organizations.tasks.organization_invite.send_invite_email.EmailMultiAlternatives.send",
                side_effect=Exception("SMTP connection failed"),
            ),
            caplog.at_level("WARNING"),
        ):
            try:
                send_invite_email_task.apply(
                    args=[invite.id, "raw-token-123"], throw=True
                ).get()
            except Retry:
                pass

        assert any(
            "Не удалось отправить письмо" in record.message for record in caplog.records
        )

    def test_retry_called_with_original_exception(self, invite):
        original_exc = ConnectionError("SMTP timeout")

        with (
            patch(
                "apps.organizations.tasks.organization_invite.send_invite_email.EmailMultiAlternatives.send",
                side_effect=original_exc,
            ),
            patch.object(
                send_invite_email_task, "retry", side_effect=Retry()
            ) as mocked_retry,
        ):
            with pytest.raises(Retry):
                send_invite_email_task(invite.id, "raw-token-123")

            mocked_retry.assert_called_once()
            _, kwargs = mocked_retry.call_args
            assert kwargs["exc"] is original_exc


class TestSendInviteEmailTaskContext:
    def test_organization_relation_is_prefetched(
        self, invite, django_assert_num_queries
    ):
        """
        Проверяем, что select_related("organization") действительно
        экономит запрос при обращении к invite.organization.name.
        """
        with django_assert_num_queries(1):
            fetched = OrganizationInvite.objects.select_related("organization").get(
                id=invite.id
            )
            _ = fetched.organization.name
