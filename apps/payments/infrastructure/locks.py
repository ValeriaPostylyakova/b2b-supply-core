import logging
import uuid
from contextlib import contextmanager

from django_redis import get_redis_connection

logger = logging.getLogger(__name__)


RELEASE_LOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


@contextmanager
def redis_webhook_lock(payment_id: str, expire_seconds: int = 30):
    redis_conn = get_redis_connection("default")
    lock_key = f"lock:webhook:yookassa:{payment_id}"
    lock_value = str(uuid.uuid4())

    is_acquired = redis_conn.set(lock_key, lock_value, ex=expire_seconds, nx=True)

    if not is_acquired:
        logger.warning(
            "Вебхук пропущен: платеж %s уже обрабатывается (активна блокировка Redis)",
            payment_id,
        )
        raise ValueError("Already processing")

    try:
        yield
    finally:
        try:
            released = redis_conn.eval(RELEASE_LOCK_LUA, 1, lock_key, lock_value)

            if released:
                logger.debug(
                    "Блокировка Redis успешно снята для платежа %s", payment_id
                )
            else:
                logger.warning(
                    "Не удалось снять блокировку для %s: таймаут истек и ключ занят другим процессом",
                    payment_id,
                )
        except Exception as e:
            logger.error(
                "Ошибка при попытке снять блокировку Redis для %s: %s", payment_id, e
            )
