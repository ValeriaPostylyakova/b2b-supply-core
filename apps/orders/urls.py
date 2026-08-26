from rest_framework.routers import DefaultRouter

from apps.orders.views import OrdersViewSet

router = DefaultRouter()

router.register("orders", OrdersViewSet, basename="orders")

urlpatterns = []

urlpatterns += router.urls
