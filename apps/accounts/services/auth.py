import time

from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

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
