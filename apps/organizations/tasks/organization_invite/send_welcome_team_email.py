import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from apps.organizations.models.organization import Organization

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(
    name="organizations.send_welcome_team_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_welcome_team_email_task(self, user_id, organization_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(
            f"Пользователь с ID {user_id} не найден. Отправка приветственного письма отменена."
        )
        return False

    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        logger.error(
            f"Организация с ID {organization_id} не найдена. Отправка приветственного письма отменена."
        )
        return False

    context = {
        "username": user.username,
        "organization_name": organization.name,
        "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
    }

    subject = f"Добро пожаловать в команду {organization.name}!"
    html_message = render_to_string("emails/welcome_team.html", context)
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = user.email

    try:
        mail = EmailMultiAlternatives(
            subject=subject, body=plain_message, from_email=from_email, to=[to_email]
        )
        mail.attach_alternative(html_message, "text/html")
        mail.send(fail_silently=False)

        logger.info(
            f"Приветственное письмо успешно отправлено на {to_email} (ID пользователя: {user_id}, ID организации: {organization_id})"
        )
        return True

    except Exception as exc:
        current_retry = self.request.retries
        logger.warning(
            f"Не удалось отправить приветственное письмо на {to_email}. "
            f"Попытка {current_retry + 1} из {self.max_retries + 1}. Ошибка: {exc}"
        )
        raise self.retry(exc=exc)
