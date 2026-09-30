from django.urls import path

from apps.payments.api.views import PaymentView
from apps.payments.api.webhooks import YookassaWebhookView

urlpatterns = [
    path("", PaymentView.as_view(), name="init"),
    path("ookassa/webhook/", YookassaWebhookView.as_view(), name="yookassa_webhook"),
]
