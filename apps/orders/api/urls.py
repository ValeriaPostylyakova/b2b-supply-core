from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.orders.api.views.order import OrderExistsView, OrderViewSet

router = DefaultRouter()
router.register("", OrderViewSet, basename="orders")

urlpatterns = [
     path(
        "<uuid:external_id>/exists/",
        OrderExistsView.as_view(),
        name="order-exists",
    ),
]

urlpatterns += router.urls
