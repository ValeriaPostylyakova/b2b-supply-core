from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
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


@extend_schema(tags=["Авторизация"])
class CookieTokenObtainView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle]
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        summary="Получить токены",
        description="Вход по email и паролю. Вернёт access и данные пользователя; refresh сохранится в HttpOnly-cookie.",
        examples=[OpenApiExample("Вход", value={"email": "buyer@example.com", "password": "StrongPass123!"}, request_only=True)],
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        return AuthService.set_refresh_token_cookie(response)


@extend_schema(tags=["Авторизация"])
class CookieTokenRefreshView(TokenRefreshView):
    @extend_schema(summary="Обновить access-токен", description="Берёт refresh из HttpOnly-cookie. В Swagger сначала выполните вход; cookie должна сохраниться в браузере.")
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


@extend_schema(tags=["Авторизация"])
class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Выйти из аккаунта", description="Отзывает refresh-токен и удаляет cookie. Требуется авторизация.")
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


@extend_schema(tags=["Восстановление пароля"])
class RequestOTPAPIView(APIView):
    throttle_classes = [OTPRequestRateThrottle]
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Запросить код восстановления", description="Отправляет одноразовый код на email. Код понадобится на следующем шаге.", request=RequestOTPSerializer, examples=[OpenApiExample("Запрос кода", value={"email": "buyer@example.com"}, request_only=True)])
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        AuthService.send_otp_email(email)

        return Response(
            {"detail": "Письмо отправлено на почту."}, status=status.HTTP_200_OK
        )


@extend_schema(tags=["Восстановление пароля"])
class VerifyOTPAPIView(APIView):
    throttle_classes = [OTPVerifyRateThrottle]
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Подтвердить код", description="Проверяет OTP и возвращает reset_token. Передайте его в запрос смены пароля.", request=VerifyOTPSerializer, examples=[OpenApiExample("Проверка кода", value={"email": "buyer@example.com", "otp": "123456"}, request_only=True)])
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


@extend_schema(tags=["Восстановление пароля"])
class ResetPasswordAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Установить новый пароль", description="Использует reset_token из шага подтверждения. Пароли должны совпадать.", request=ResetPasswordSerializer, examples=[OpenApiExample("Новый пароль", value={"token": "<reset_token>", "new_password": "NewStrongPass123!", "confirm_password": "NewStrongPass123!"}, request_only=True)])
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        AuthService.reset_password_with_token(token, new_password)

        return Response(
            {"detail": "Пароль успешно изменен."}, status=status.HTTP_200_OK
        )


@extend_schema_view(
    get=extend_schema(summary="Мой профиль", description="Возвращает профиль текущего пользователя."),
    patch=extend_schema(summary="Обновить профиль", description="Обновляет имя, фамилию и аватар. Роль и организацию менять нельзя."),
)
@extend_schema(tags=["Профиль"])
class MeAPIView(RetrieveUpdateAPIView):
    queryset = User.objects.all().select_related("organization")
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user
