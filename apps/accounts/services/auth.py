import secrets
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django_redis import get_redis_connection
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tasks.auth import send_otp_email_task
from apps.common.jwt_blacklist import JwtBlacklist


class AuthService:
    @staticmethod
    def set_refresh_token_cookie(response):
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

    @staticmethod
    def blacklist_token(refresh_token_str: str):
        refresh = RefreshToken(refresh_token_str)

        jti = refresh["jti"]
        now = int(time.time())
        ttl = int(refresh["exp"] - now)

        if ttl > 0:
            blacklist = JwtBlacklist()
            blacklist.revoke(jti, ttl)

    @staticmethod
    def send_otp_email(email: str):
        User = get_user_model()
        user = get_object_or_404(User, email=email)

        otp = OTPService.generate_otp(user.email)
        send_otp_email_task.delay(user.email, otp)

    @staticmethod
    def generate_reset_token(otp: str, email: str):
        User = get_user_model()
        user = get_object_or_404(User, email=email)

        is_valid = OTPService.verify_otp(user.email, otp)
        if not is_valid:
            raise ValidationError({"otp": "Неверный или истекший код подтверждения."})

        token = signing.dumps({"email": user.email}, salt="password-reset-salt")
        return token

    @staticmethod
    def reset_password_with_token(token: str, new_password: str):
        try:
            data = signing.loads(token, salt="password-reset-salt", max_age=600)
        except signing.SignatureExpired:
            raise ValidationError({"token": "Срок действия токена истек."})
        except signing.BadSignature:
            raise ValidationError({"token": "Невалидный токен."})

        User = get_user_model()
        email = data.get("email")

        user = get_object_or_404(User, email=email)

        user.set_password(new_password)
        user.save()


class OTPService:
    @staticmethod
    def otp_key(email: str) -> str:
        return f"otp:user:{email}"

    @staticmethod
    def generate_otp(email: str) -> str:
        otp = str(secrets.randbelow(1_000_000)).zfill(6)
        redis = get_redis_connection("default")
        key = OTPService.otp_key(email)

        redis.set(key, otp, ex=300)

        return otp

    @staticmethod
    def verify_otp(email: str, otp: str) -> bool:
        redis = get_redis_connection("default")

        key = OTPService.otp_key(email)

        otp_from_redis = redis.get(key)

        if otp_from_redis is None:
            return False

        if otp_from_redis.decode("utf-8") != otp:
            return False

        redis.delete(key)
        return True
