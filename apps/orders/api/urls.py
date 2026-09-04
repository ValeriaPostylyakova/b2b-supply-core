from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.orders.api.views.order import OrderViewSet
from apps.orders.api.views.order_invoice import OrderInvoiceView

router = DefaultRouter()

router.register("orders", OrderViewSet, basename="orders")

urlpatterns = [
    path(
        "orders/<str:external_id>/invoice/",
        OrderInvoiceView.as_view(),
        name="order-invoice-create",
    ),
    path(
        "orders/invoice-status/<str:task_id>/",
        OrderInvoiceView.as_view(),
        name="order-invoice-status",
    ),
]

urlpatterns += router.urls
