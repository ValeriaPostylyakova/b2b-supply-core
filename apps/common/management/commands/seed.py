from django.core.management.base import BaseCommand
from django.db import transaction
from ._seeders import clean_old_data, seed_base_data, seed_products_and_warehouses, seed_stocks

class Command(BaseCommand):
    help = 'Заполняет БД тестовыми данными: Организации, Пользователи, Продукты, Склады и Остатки'

    def add_arguments(self, parser):
        parser.add_argument(
            '--orgs',
            type=int,
            default=5,
            help='Количество создаваемых организаций каждого типа'
        )

    def handle(self, *args, **options):
        org_count = options['orgs']

        self.stdout.write(self.style.WARNING('Очистка старых тестовых данных...'))
        clean_old_data()

        self.stdout.write(self.style.WARNING('Начало генерации данных...'))

        try:
            with transaction.atomic():
                suppliers = seed_base_data(org_count)
                self.stdout.write(self.style.SUCCESS(
                    f'Шаг 1 завершен: {org_count * 2} организаций и пользователи созданы.'
                ))

                products, warehouses = seed_products_and_warehouses(suppliers)
                self.stdout.write(self.style.SUCCESS(
                    f'Шаг 2 завершен: Создано {len(products)} продуктов и {len(warehouses)} складов.'
                ))

                stocks_count = seed_stocks(products, warehouses)
                self.stdout.write(self.style.SUCCESS(
                    f'Шаг 3 завершен: Распределено {stocks_count} записей остатков по складам.'
                ))

            self.stdout.write(self.style.SUCCESS('🎉 Сидирование успешно завершено! Все связи соблюдены.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Ошибка при генерации данных: {e}'))
            self.stdout.write(self.style.ERROR('База данных автоматически откачена к исходному состоянию.'))
