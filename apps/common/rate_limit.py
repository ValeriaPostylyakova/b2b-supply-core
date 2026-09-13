from django_redis import get_redis_connection


class RedisRateLimiter:
    def __init__(self, limit: 5, window: 60):
        self.limit = limit
        self.window = window

    def is_allowed(self, key: str) -> bool:
        redis = get_redis_connection("default")

        current = redis.incr(key)

        if current == 1:
            redis.expire(key, self.window)

        return current <= self.limit

    def get_current_count(self, key: str) -> int:
        redis = get_redis_connection("default")

        value = redis.get(key)

        return int(value or 0)

    def get_ttl(self, key: str) -> int:
        redis = get_redis_connection("default")

        return redis.ttl(key)
