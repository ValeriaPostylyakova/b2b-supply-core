import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from apps.organizations.models.organization_invite import OrganizationInvite

logger = logging.getLogger(__name__)


@shared_task(
    name="organizations.send_invite_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_invite_email_task(self, invite_id: int, raw_token: str):
    try:
        invite = OrganizationInvite.objects.select_related("organization").get(
            id=invite_id
        )
    except OrganizationInvite.DoesNotExist:
        logger.error(f"Invite with id {invite_id} not found. Task aborted.")
        return False

    context = {
        "organization_name": invite.organization.name,
        "accept_url": f"{settings.FRONTEND_URL}/invite/accept/?token={raw_token}",
        "raw_token": raw_token,
    }

    subject = f"Приглашение в организацию {invite.organization.name}"
    html_message = render_to_string("emails/organization_invite.html", context)
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = invite.email

    try:
        mail = EmailMultiAlternatives(
            subject=subject, body=plain_message, from_email=from_email, to=[to_email]
        )
        mail.attach_alternative(html_message, "text/html")
        mail.send(fail_silently=False)

        logger.info(
            f"Invite email successfully sent to {to_email} (Invite ID: {invite_id})"
        )
        return True

    except Exception as exc:
        logger.warning(
            f"Failed to send invite email to {to_email}. "
            f"Retrying ({self.request.retries}/{self.max_retries})... Error: {exc}"
        )
        raise self.retry(exc=exc)
