from django.urls import URLPattern, URLResolver, path
from rest_framework.routers import DefaultRouter

from apps.catalog.api.views.price_list import (
    PriceListCreateAPIView,
    PriceListPresignedUrlAPIView,
    PriceListRetrieveAPIView,
)
from apps.catalog.api.views.product import ProductViewSet
from apps.catalog.api.views.stock import StockViewSet
from apps.catalog.api.views.warehouse import WarehouseViewSet

router = DefaultRouter()
router.register("warehouses", WarehouseViewSet, basename="warehouse")
router.register("products", ProductViewSet, basename="product")
router.register("stocks", StockViewSet, basename="stock")

urlpatterns: list[URLPattern | URLResolver] = [
    path(
        "price-list/upload-url/",
        PriceListPresignedUrlAPIView.as_view(),
        name="price-list-upload-url",
    ),
    path("price-list/", PriceListCreateAPIView.as_view(), name="price-list-import"),
    path(
        "price-list/<str:external_id>/",
        PriceListRetrieveAPIView.as_view(),
        name="price-list-retrieve",
    ),
]

urlpatterns += router.urls
