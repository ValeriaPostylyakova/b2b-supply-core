import random
from itertools import islice

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.catalog.models import Product, Warehouse


class Command(BaseCommand):
    help = "Генерация 1 миллиона тестовых продуктов"

    def handle(self, *args, **options):
        # Получаем ID всех поставщиков
        supplier_ids = list(
            Warehouse.objects.values_list("supplier_id", flat=True).distinct()
        )

        if not supplier_ids:
            self.stdout.write(
                self.style.ERROR("Сначала добавьте поставщиков и склады в БД!")
            )
            return

        total_records = 1_000_000  # Поставили 1 миллион
        batch_size = 5_000

        self.stdout.write(f"Начало генерации {total_records:,} записей...")

        def product_generator():
            for i in range(1, total_records + 1):
                yield Product(
                    sku=f"SKU-{i:08d}",
                    name=f"Товар {i} (Тест)",
                    price=round(random.uniform(100.00, 15000.00), 2),
                    description=f"Тестовое описание для товара под номером {i}.",
                    is_active=random.choice([True, True, False]),
                    supplier_id=random.choice(supplier_ids),
                )

        products_iter = product_generator()
        inserted_count = 0

        with transaction.atomic():
            while True:
                batch = list(islice(products_iter, batch_size))
                if not batch:
                    break

                Product.objects.bulk_create(
                    batch, batch_size=batch_size, ignore_conflicts=True
                )

                inserted_count += len(batch)

                # Очищаем память Django от логов SQL-запросов
                connection.queries_log.clear()

                # Выводим прогресс каждые 50 000 записей
                if inserted_count % 50_000 == 0:
                    percent = (inserted_count / total_records) * 100
                    self.stdout.write(
                        f"Успешно записано: {inserted_count:,} / {total_records:,} ({percent:.1f}%)"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Генерация {total_records:,} записей успешно завершена!"
            )
        )
