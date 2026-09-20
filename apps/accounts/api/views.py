from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.api.serializers import (
    CustomTokenObtainPairSerializer,
    MeSerializer,
    RequestOTPSerializer,
    ResetPasswordSerializer,
    VerifyOTPSerializer,
)
from apps.accounts.services.auth import AuthService
from apps.common.jwt_blacklist import JwtBlacklist
from apps.common.throttles.otp import (
    LoginRateThrottle,
    OTPRequestRateThrottle,
    OTPVerifyRateThrottle,
)
from config.settings import base as settings

User = get_user_model()


class CookieTokenObtainView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle]
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        return AuthService.set_refresh_token_cookie(response)


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request: Request, *args, **kwargs) -> Response:
        cookie_name = settings.SIMPLE_JWT["AUTH_COOKIE"]
        refresh_token = request.COOKIES.get(cookie_name)

        if not refresh_token:
            return Response({"detail": "Credentials not provided."}, status=401)

        blacklist = JwtBlacklist()
        try:
            old_refresh = RefreshToken(refresh_token)
            old_jti = old_refresh["jti"]

            if blacklist.is_revoked(old_jti):
                return Response({"detail": "Token has been revoked."}, status=401)
        except (TokenError, InvalidToken):
            return Response({"detail": "Token is invalid or expired."}, status=401)

        request._full_data = {"refresh": refresh_token}
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            ttl = old_refresh["exp"] - old_refresh["iat"]
            blacklist.revoke(old_jti, ttl=ttl)

            response = AuthService.set_refresh_token_cookie(response)
        return response


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE", "refresh_token")
        refresh_token = request.COOKIES.get(cookie_name)
        if not refresh_token:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=401,
            )

        try:
            AuthService.blacklist_token(refresh_token)

            response = Response({"detail": "Successfully logged out."}, status=200)
            response.delete_cookie(
                cookie_name, path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/")
            )
            return response

        except (TokenError, InvalidToken):
            return Response({"detail": "Invalid or expired token."}, status=400)


class RequestOTPAPIView(APIView):
    throttle_classes = [OTPRequestRateThrottle]

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        AuthService.send_otp_email(email)

        return Response(
            {"detail": "Письмо отправлено на почту."}, status=status.HTTP_200_OK
        )


class VerifyOTPAPIView(APIView):
    throttle_classes = [OTPVerifyRateThrottle]

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data["otp"]
        email = serializer.validated_data["email"]

        reset_token = AuthService.generate_reset_token(otp, email)

        return Response(
            {
                "detail": "Код успешно подтвержден.",
                "reset_token": reset_token,
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        AuthService.reset_password_with_token(token, new_password)

        return Response(
            {"detail": "Пароль успешно изменен."}, status=status.HTTP_200_OK
        )


class MeAPIView(RetrieveUpdateAPIView):
    queryset = User.objects.all().select_related("organization")
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user
