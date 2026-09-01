from django.urls import URLPattern, URLResolver, path
from rest_framework.routers import DefaultRouter

from apps.catalog.views import (
    PriceListCreateAPIView,
    PriceListPresignedUrlAPIView,
    PriceListRetrieveAPIView,
    ProductViewSet,
    StockViewSet,
    WarehouseViewSet,
)

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
