import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


app.conf.beat_schedule = {
    "clear_expired_reservations_every_5_minutes": {
        "task": "orders.clear_expired_reservations",
        "schedule": crontab(minute="*/5"),
    },
    "clear_expired_invite_at_3_am": {
        "task": "organizations.clear_expired_invite",
        "schedule": crontab(hour=3, minute=0),
    },
}
