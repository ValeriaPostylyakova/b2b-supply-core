import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from faker import Faker
from apps.accounts.models import Organization

User = get_user_model()
fake = Faker(['ru_RU'])


class Command(BaseCommand):
    help = 'Заполняет базу данных реалистичными тестовыми данными'

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
        User.objects.filter(email__endswith='@example.com').delete()
        Organization.objects.filter(name__endswith=' (Тест)').delete()

        self.stdout.write(self.style.SUCCESS('Начало генерации данных...'))

        suppliers = []
        buyers = []

        for _ in range(org_count):
            supplier = Organization.objects.create(
                name=f"ООО {fake.company()} (Тест)",
                type=Organization.Types.SUPPLIER
            )
            suppliers.append(supplier)

            buyer = Organization.objects.create(
                name=f"ИП {fake.company()} (Тест)",
                type=Organization.Types.BUYER
            )
            buyers.append(buyer)

        for org in suppliers:
            User.objects.create_user(
                email=fake.unique.email(domain='example.com'),
                username=fake.unique.user_name(),
                password='password123',
                first_name=fake.first_name_male(),
                last_name=fake.last_name_male(),
                role=User.Roles.SUPPLIER_ADMIN,
                organization=org
            )
            for _ in range(random.randint(1, 3)):
                User.objects.create_user(
                    email=fake.unique.email(domain='example.com'),
                    username=fake.unique.user_name(),
                    password='password123',
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    role=User.Roles.SUPPLIER_MANAGER,
                    organization=org
                )

        for org in buyers:
            User.objects.create_user(
                email=fake.unique.email(domain='example.com'),
                username=fake.unique.user_name(),
                password='password123',
                first_name=fake.first_name_female(),
                last_name=fake.last_name_female(),
                role=User.Roles.BUYER_ADMIN,
                organization=org
            )

            User.objects.create_user(
                email=fake.unique.email(domain='example.com'),
                username=fake.unique.user_name(),
                password='password123',
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                role=User.Roles.BUYER_MANAGER,
                organization=org
            )

        self.stdout.write(self.style.SUCCESS(
            f'Готово! Создано {org_count * 2} организаций и связанные пользователи.'
        ))
