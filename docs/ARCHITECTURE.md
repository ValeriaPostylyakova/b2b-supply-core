# Архитектура

Монолит на Django с разделением по доменным приложениям. Внутри приложения слои: `api` (views, serializers, filters) → `services` (бизнес-логика) → `models`; фоновые задачи лежат в `tasks`.

## Роли

| Роль | Организация |
|---|---|
| `SUPPLIER_ADMIN`, `SUPPLIER_MANAGER`, `WAREHOUSE_MANAGER` | поставщик |
| `BUYER_ADMIN`, `BUYER_MANAGER` | покупатель |

Права проверяются классами `permissions` в каждом приложении; организация должна быть верифицирована.

## Ключевые процессы

### Заказ

```
RESERVED ──оплата──► PAID ──подтверждение──► CONFIRMED
    └──────────────────┴──отмена──► CANCELLED
```

Статусы `DRAFT` и `COMPLETED` предусмотрены моделью, переходов в них пока нет.

1. Создание заказа блокирует строки остатков (`select_for_update`), увеличивает `reserved_quantity` и создаёт `Reservation` на 1 час.
2. Beat раз в 10 минут (`orders.clear_expired_reservation`) снимает просроченные резервы.
3. Отмена возвращает резерв в доступный остаток.

### Оплата (ЮKassa)

Платёж создаётся с `idempotence_key`. Webhook обрабатывается под Redis-локом `lock:webhook:yookassa:<payment_id>`, повторные уведомления безопасны. При `payment.succeeded` заказ переходит в `PAID`.

### Импорт прайс-листа

1. `POST /api/v1/price-list/upload-url/` — presigned PUT URL.
2. Клиент загружает `.xlsx` в приватный бакет.
3. `POST /api/v1/price-list/` — создаётся `PriceListImport`, задача уходит в очередь `heavy_tasks`.
4. `GET /api/v1/price-list/<id>/` — статус и счётчики строк (`total / success / error`).

### Transactional Outbox

Событие (`order.confirmed`) пишется в таблицу `OutboxEvent` в той же транзакции, что и изменение заказа. Beat каждые 5 секунд запускает `common.publish_outbox_events`: задача берёт пачку `PENDING` через `select_for_update(skip_locked=True)` и публикует в exchange `b2b.events` (topic) с подтверждением доставки. Потерь события при падении брокера нет, параллельные воркеры не пересекаются.

## Очереди Celery

| Очередь | Задачи |
|---|---|
| `high_priority` | зарезервирована под срочные задачи |
| `default` | остальные (почта, резервы, outbox) |
| `heavy_tasks` | импорт прайс-листов |

## Где что хранится

| Хранилище | Назначение |
|---|---|
| PostgreSQL | основные данные, outbox |
| Redis | кэш, OTP, blacklist JWT, рейт-лимиты, локи, результаты Celery |
| RabbitMQ | брокер Celery, внешние события |
| S3 | публичный бакет (аватары), приватный (прайс-листы, presigned URL) |

## API

Контракт генерируется автоматически: `/api/schema/`, Swagger — `/api/docs/swagger/`, ReDoc — `/api/docs/redoc/`. Лимиты запросов (throttling) заданы в `REST_FRAMEWORK` в `config/settings/base.py`.
