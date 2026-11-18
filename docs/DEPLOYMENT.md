# Деплой

Схема: `reverse proxy (TLS)` → `web (gunicorn)`; рядом `worker`, `beat`, PostgreSQL, Redis, RabbitMQ. Файлы хранятся во внешнем S3.

## Требования

- Docker и Docker Compose v2
- Домен и reverse proxy с TLS (nginx / Caddy / Traefik)
- S3-совместимое хранилище с двумя бакетами (публичный и приватный)
- SMTP-аккаунт и магазин ЮKassa

## 1. Настройка

```bash
cp .env.prod.example .env.prod
```

Заполните `.env.prod`. Обязательно:

| Переменная | Описание |
|---|---|
| `SECRET_KEY` | уникальный ключ (команда для генерации — в файле) |
| `ALLOWED_HOSTS` | домены через запятую; первый — реальный домен (его использует healthcheck) |
| `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` | адреса API и фронтенда с `https://` |
| `DB_*`, `RABBITMQ_*` | пароли БД и брокера; в `RABBITMQ_URL` и `CELERY_BROKER_URL` подставьте тот же пароль (спецсимволы — в URL-кодировке) |
| `S3_*` | эндпоинт, ключи, имена бакетов |
| `EMAIL_*`, `YOOKASSA_*`, `PAYMENT_RETURN_URL` | почта и платежи |

## 2. Запуск

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

При старте `web` сам выполняет `migrate` и `collectstatic`. Статика отдаётся через WhiteNoise.

Проверка:

```bash
docker compose -f docker-compose.prod.yml ps
curl https://api.example.com/health/        
```

## 3. Reverse proxy

Проксируйте домен на `127.0.0.1:8000` и передавайте заголовки `Host` и `X-Forwarded-Proto: https`. Пример для nginx:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    client_max_body_size 20m;
}
```

## 4. Первичная настройка

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

В личном кабинете ЮKassa укажите URL уведомлений: `https://api.example.com/api/v1/payments/ookassa/webhook/` (в маршруте именно `ookassa`).

Команду `seed` на продакшене не запускать: она удаляет данные заказов, остатков и тестовые записи.

## Обновление

```bash
git pull
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

## Резервные копии

```bash
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U $DB_USER $DB_NAME > backup.sql
```

Тома `pg_data`, `redis_data`, `rabbitmq_data` хранят состояние; Redis содержит OTP и blacklist токенов, RabbitMQ — неотправленные сообщения.
