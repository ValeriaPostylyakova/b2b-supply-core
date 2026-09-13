import hashlib

from django_redis import get_redis_connection
from rest_framework.throttling import BaseThrottle

from apps.common.rate_limit import RedisRateLimiter


class LoginRateThrottle(BaseThrottle):
    ip_limit = 20
    user_limit = 5
    window = 60

    def allow_request(self, request, view):
        self.limiter = RedisRateLimiter(
            limit=5,
            window=60,
        )

        ip = self.get_ident(request)
        self.ip_key = f"rate-limit:login:ip:{ip}"

        if not self.limiter.is_allowed(self.ip_key):
            self.wait_key = self.ip_key
            return False

        email = request.data.get("email")

        if email:
            email = email.strip().lower()

            email_hash = hashlib.sha256(email.encode()).hexdigest()

            self.user_key = f"rate-limit:login:user:{email_hash}"

            self.user_limiter = RedisRateLimiter(
                limit=self.user_limit,
                window=self.window,
            )

            if not self.user_limiter.is_allowed(self.user_key):
                self.wait_key = self.user_key
                return False

        return True

    def wait(self):
        if hasattr(self, "wait_key"):
            redis = get_redis_connection("default")
            return redis.ttl(self.wait_key)

        return None
