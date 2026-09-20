import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


@shared_task(
    name="accounts.send_otp_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_otp_email_task(self, email, otp):
    subject = "Восстановление пароля | Код подтверждения"
    from_email = settings.DEFAULT_FROM_EMAIL

    context = {"otp": otp}

    html_content = render_to_string("auth/send_otp_email.html", context)
    text_content = strip_tags(html_content)

    try:
        logger.info(f"Отправка кода сброса пароля на email {email}")

        msg = EmailMultiAlternatives(subject, text_content, from_email, [email])
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        logger.info(f"Код сброса пароля успешно отправлен на email {email}")
        return f"Reset code sent to {email}"

    except Exception as exc:
        logger.error(f"Ошибка при отправке кода сброса на {email}: {exc}")
        raise self.retry(exc=exc)
