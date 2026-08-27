import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматически ищем задачи (tasks.py) в зарегистрированных приложениях django (INSTALLED_APPS)
app.autodiscover_tasks()
