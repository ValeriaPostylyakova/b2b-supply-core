from django.urls import URLPattern, URLResolver, path, include
from rest_framework.routers import SimpleRouter

from apps.catalog.views import (
    ProductListAPIView,
    ProductRetrieveAPIView,
    ProductCreateAPIView,
    ProductUpdateAPIView,
    ProductDestroyAPIView,
)

urlpatterns: list[URLPattern | URLResolver] = [
    path("products/", ProductListAPIView.as_view(), name="product-list"),
    path("products/create/", ProductCreateAPIView.as_view(), name="product-create"),
    path(
        "products/<uuid:external_id>/",
        ProductRetrieveAPIView.as_view(),
        name="product-detail",
    ),
    path(
        "products/<uuid:external_id>/edit/",
        ProductUpdateAPIView.as_view(),
        name="product-update",
    ),
    path(
        "products/<uuid:external_id>/delete/",
        ProductDestroyAPIView.as_view(),
        name="product-delete",
    ),
]
