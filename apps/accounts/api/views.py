from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.api.serializers import (
    CustomTokenObtainPairSerializer,
    ProfileSerializer,
)
from config.settings import base as settings

User = get_user_model()


class CookieTokenObtainView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            refresh_token = response.data.pop("refresh")

            response.set_cookie(
                key=settings.SIMPLE_JWT["AUTH_COOKIE"],
                value=refresh_token,
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=3600 * 24,
            )
        return response


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request: Request, *args, **kwargs) -> Response:
        cookie_name = settings.SIMPLE_JWT["AUTH_COOKIE"]
        refresh_token = request.COOKIES.get(cookie_name)

        if refresh_token:
            request.data["refresh"] = refresh_token
        return super().post(request, *args, **kwargs)


class AccountProfileAPIView(RetrieveUpdateAPIView):
    queryset = User.objects.all().select_related("organization")
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user
