from django.urls import URLPattern, URLResolver, path
from apps.catalog.views import ProductListGenericAPIView

urlpatterns: list[URLPattern | URLResolver] = [
    path("products/", ProductListGenericAPIView.as_view(), name="products"),
]