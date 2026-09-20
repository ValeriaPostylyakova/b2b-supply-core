from django.urls import URLPattern, URLResolver, path
from rest_framework.routers import DefaultRouter

from apps.accounts.api.views import (
    CookieTokenObtainView,
    CookieTokenRefreshView,
    LogoutAPIView,
    MeAPIView,
    RequestOTPAPIView,
    ResetPasswordAPIView,
    VerifyOTPAPIView,
)

router = DefaultRouter()


urlpatterns: list[URLPattern | URLResolver] = [
    path("auth/token/", CookieTokenObtainView.as_view(), name="token_obtain"),
    path("auth/token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("auth/request-otp/", RequestOTPAPIView.as_view(), name="request-otp"),
    path("auth/verify-otp/", VerifyOTPAPIView.as_view(), name="verify-otp"),
    path("auth/reset-password/", ResetPasswordAPIView.as_view(), name="reset-password"),
    path("auth/me/", MeAPIView.as_view(), name="profile"),
]

urlpatterns += router.urls
