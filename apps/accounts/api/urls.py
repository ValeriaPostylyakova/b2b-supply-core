from django.urls import URLPattern, URLResolver, path
from rest_framework.routers import DefaultRouter

from apps.accounts.api.views import (
    CookieTokenObtainView,
    CookieTokenRefreshView,
    MeAPIView,
)

router = DefaultRouter()


urlpatterns: list[URLPattern | URLResolver] = [
    path("auth/token/", CookieTokenObtainView.as_view(), name="token_obtain"),
    path("auth/token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeAPIView.as_view(), name="profile"),
]

urlpatterns += router.urls
