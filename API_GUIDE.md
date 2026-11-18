# API — быстрый старт и сценарии

Swagger UI: `http://localhost:8000/api/docs/swagger/`  
OpenAPI JSON: `http://localhost:8000/api/schema/`  
ReDoc: `http://localhost:8000/api/docs/redoc/`

## Как выполнять запросы в Swagger

1. Войдите через `POST /api/v1/auth/token/` — укажите email и пароль существующего пользователя.
2. Скопируйте `access` из ответа, нажмите **Authorize** и вставьте только токен (без `Bearer`).
3. Откройте endpoint → **Try it out** → заполните поля → **Execute**.
4. Успешные ответы имеют обёртку `success`, `data`, `error`. В `data` находится результат операции.

`refresh` хранится в HttpOnly-cookie браузера. Обновление токена выполняйте в том же браузере через `POST /api/v1/auth/token/refresh/`.

## Сценарий 1. Поставщик публикует каталог

Нужен пользователь с ролью `SUPPLIER_ADMIN` в подтверждённой организации.

1. Создайте склад: `POST /api/v1/warehouses/`.

```json
{
  "name": "Основной склад",
  "address": "Москва, ул. Пример, 1"
}
```

2. Загрузите прайс-лист (сценарий 2). В колонке `warehouse` укажите `Основной склад`.
3. Проверьте результат через `GET /api/v1/price-list/{import_id}/`.
4. После импорта найдите товар через `GET /api/v1/products/?search=название`.

## Сценарий 2. Импорт прайс-листа Excel

Нужен `SUPPLIER_ADMIN` подтверждённой организации и активный склад. Поддерживаются `.xlsx` и `.xls`.

1. Получите ссылку: `POST /api/v1/price-list/upload-url/`.

```json
{ "file_name": "price-list.xlsx" }
```

2. Выполните `PUT` на полученный `upload_url`, передав бинарное содержимое Excel-файла. Например:

```bash
curl -X PUT "<upload_url>" \
  --upload-file price-list.xlsx \
  -H "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
```

3. Запустите импорт: `POST /api/v1/price-list/`.

```json
{
  "storage_key": "<storage_key из шага 1>",
  "original_name": "price-list.xlsx"
}
```

4. Сохраните `id` из ответа и опрашивайте `GET /api/v1/price-list/{id}/` до конечного статуса.

Excel должен содержать заголовки `sku`, `name`, `price`, `warehouse`, `quantity`. `warehouse` — точное имя существующего активного склада. Импорт создаёт или обновляет товар и остаток. Возможные статусы: `PENDING`, `PROCESSING`, `COMPLETED`, `COMPLETED_WITH_ERRORS`, `FAILED`.

## Сценарий 3. Покупатель оформляет заказ и оплачивает

Нужны подтверждённые организации покупателя и поставщика, опубликованный товар и доступный остаток. Для создания заказа пользователь должен иметь роль покупателя.

1. Найдите товар: `GET /api/v1/products/?search=название`.
2. Из ответа возьмите UUID товара (`id`), склада (`warehouses[].id`) и поставщика (`supplier.id` или UUID организации поставщика из карточки).
3. Создайте заказ: `POST /api/v1/orders/`.

```json
{
  "supplier": "<supplier_uuid>",
  "items": [
    {
      "product": "<product_uuid>",
      "warehouse": "<warehouse_uuid>",
      "quantity": 2
    }
  ]
}
```

4. Сохраните `id` заказа из ответа. Статус после создания — `RESERVED`; количество резервируется.
5. Создайте платёж: `POST /api/v1/payments/`.

```json
{ "order_id": "<order_uuid>" }
```

6. Откройте `confirmation_url` из ответа и завершите оплату в YooKassa. После подтверждённого webhook заказ получает статус `PAID`.
7. Поставщик подтверждает заказ: `POST /api/v1/orders/{order_id}/confirm/`. Статус становится `CONFIRMED`.

Альтернатива: покупатель может вызвать `POST /api/v1/orders/{order_id}/cancel/` для отмены заказа и освобождения резерва (если текущий статус допускает отмену).

## Сценарий 4. Приглашение сотрудника

Нужен администратор организации (`SUPPLIER_ADMIN` или `BUYER_ADMIN`).

1. Создайте приглашение: `POST /api/v1/organizations/my-company/invites/`.

```json
{
  "email": "employee@example.com",
  "role": "BUYER_MANAGER"
}
```

Допустимые роли: `SUPPLIER_ADMIN`, `SUPPLIER_MANAGER`, `WAREHOUSE_MANAGER`, `BUYER_ADMIN`, `BUYER_MANAGER` (роль должна соответствовать типу организации).

2. Получатель открывает ссылку из письма. Frontend передаёт токен: `POST /api/v1/organizations/my-company/invites/accept/`.

```json
{ "token": "<invite_token>" }
```

3. Если `is_new_user: true`, завершите регистрацию через `POST /api/v1/organizations/my-company/invites/register/`, передав `registration_token`, `first_name`, `last_name`, `username`, `password` из ответа предыдущего шага.

## Сценарий 5. Восстановление пароля

1. `POST /api/v1/auth/request-otp/` — `{ "email": "user@example.com" }`.
2. Получите код из письма и отправьте `POST /api/v1/auth/verify-otp/` — `{ "email": "user@example.com", "otp": "123456" }`.
3. Передайте `reset_token` из ответа в `POST /api/v1/auth/reset-password/` вместе с `new_password` и `confirm_password`.

## Полезные запросы

- `GET /api/v1/auth/me/` — проверить текущего пользователя и его роль.
- `GET /api/v1/organizations/my-company/` — проверить организацию и статус верификации.
- `GET /api/v1/stocks/` и `GET /api/v1/stocks/reports/` — остатки, резервы и доступное количество.
- `GET /api/v1/orders/` и `GET /api/v1/orders/reports/` — заказы и сводная статистика.
- `GET /api/v1/orders/{order_id}/exists/` — проверить доступ к заказу.

Для успешных запросов используйте реальные UUID и данные вашей тестовой организации. Доступность endpoint'ов зависит от роли, статуса верификации и текущего статуса заказа.
