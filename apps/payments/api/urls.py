from django.urls import path

from apps.payments.api.views import InitPaymentView, YookassaWebhookView

urlpatterns = [
    path("init/", InitPaymentView.as_view(), name="init"),
    path("ookassa/webhook/", YookassaWebhookView.as_view(), name="yookassa_webhook"),
]
