from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, URLResolver, URLPattern, include

urlpatterns: list[URLPattern | URLResolver] = [
    path(settings.ADMIN_PANEL_URL, admin.site.urls),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.orders.urls")),
    path("api/v1/", include("apps.inventory.urls")),
    path("api/v1/", include("apps.documents.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
