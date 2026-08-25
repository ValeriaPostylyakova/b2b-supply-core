from django.urls import URLPattern, URLResolver, path, include
from rest_framework.routers import DefaultRouter

from apps.catalog.views import (
    ProductViewSet,
    WarehouseViewSet,
    StockViewSet,
)

router = DefaultRouter()
router.register("warehouses", WarehouseViewSet, basename='warehouse')
router.register("products", ProductViewSet, basename='product')
router.register("stocks", StockViewSet, basename='stock')

urlpatterns: list[URLPattern | URLResolver] = []

urlpatterns += router.urls
