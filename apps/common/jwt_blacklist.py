import redis
from django.conf import settings


class JwtBlacklist:
    PREFIX = "jwt:blacklist:"

    def __init__(self):
        self.client = redis.from_url(settings.REDIS_BLACKLIST_URL)

    def get_key(self, jti: str) -> str:
        return f"{self.PREFIX}{jti}"

    def revoke(self, jti: str, ttl: int):
        key = self.get_key(jti)

        self.client.set(
            key,
            "1",
            ex=ttl,
        )

    def is_revoked(self, jti: str) -> bool:
        key = self.get_key(jti)

        return self.client.exists(key) == 1
