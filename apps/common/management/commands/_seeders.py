import random
import uuid
from django.contrib.auth import get_user_model
from faker import Faker
from apps.accounts.models import Organization
from apps.catalog.models import Product, Warehouse, Stock

User = get_user_model()
fake = Faker(["ru_RU"])


def clean_old_data():
    User.objects.filter(email__endswith="@example.com").delete()
    Organization.objects.filter(name__endswith=" (Тест)").delete()
    Stock.objects.all().delete()
    Warehouse.objects.filter(name__endswith=" (Тест)").delete()
    Product.objects.filter(name__endswith=" (Тест)").delete()


def seed_base_data(org_count):
    suppliers = []
    buyers = []

    for _ in range(org_count):
        supplier = Organization.objects.create(
            name=f"ООО {fake.company()} (Тест)", type=Organization.Types.SUPPLIER
        )
        suppliers.append(supplier)

        buyer = Organization.objects.create(
            name=f"ИП {fake.company()} (Тест)", type=Organization.Types.BUYER
        )
        buyers.append(buyer)

    for org in suppliers:
        User.objects.create_user(
            email=fake.unique.email(domain="example.com"),
            username=fake.unique.user_name(),
            password="password123",
            first_name=fake.first_name_male(),
            last_name=fake.last_name_male(),
            role=User.Roles.SUPPLIER_ADMIN,
            organization=org,
        )
        for _ in range(random.randint(1, 3)):
            User.objects.create_user(
                email=fake.unique.email(domain="example.com"),
                username=fake.unique.user_name(),
                password="password123",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                role=User.Roles.SUPPLIER_MANAGER,
                organization=org,
            )

    for org in buyers:
        User.objects.create_user(
            email=fake.unique.email(domain="example.com"),
            username=fake.unique.user_name(),
            password="password123",
            first_name=fake.first_name_female(),
            last_name=fake.last_name_female(),
            role=User.Roles.BUYER_ADMIN,
            organization=org,
        )
        User.objects.create_user(
            email=fake.unique.email(domain="example.com"),
            username=fake.unique.user_name(),
            password="password123",
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            role=User.Roles.BUYER_MANAGER,
            organization=org,
        )

    return suppliers


def seed_products_and_warehouses(suppliers):
    if not suppliers:
        return [], []

    created_products = []
    created_warehouses = []
    unit_choices = [
        Product.UnitChoices.PIECE,
        Product.UnitChoices.KILOGRAM,
        Product.UnitChoices.LITER,
    ]

    for org in suppliers:
        for _ in range(random.randint(1, 2)):
            warehouse = Warehouse.objects.create(
                name=f"Склад {fake.city()} {fake.word().capitalize()} (Тест)",
                address=fake.address(),
                is_active=True,
                supplier=org,
            )
            created_warehouses.append(warehouse)

        for _ in range(random.randint(3, 8)):
            product = Product.objects.create(
                sku=f"SKU-{fake.unique.ean(length=8)}",
                name=f"{fake.word().capitalize()} (Тест)",
                price=round(random.uniform(100.00, 15000.00), 2),
                description=fake.text(max_nb_chars=200),
                unit=random.choice(unit_choices),
                is_active=random.choice([True, True, False]),
                supplier=org,
            )
            created_products.append(product)

    return created_products, created_warehouses


def seed_stocks(products, warehouses):
    total_stocks = 0
    for warehouse in warehouses:
        supplier_products = [
            p for p in products if p.supplier_id == warehouse.supplier_id
        ]

        for product in supplier_products:
            if random.random() < 0.8:
                quantity = random.randint(10, 500)
                reserved_quantity = random.randint(
                    0, min(int(quantity * 0.2), quantity)
                )

                Stock.objects.create(
                    product=product,
                    warehouse=warehouse,
                    quantity=quantity,
                    reserved_quantity=reserved_quantity,
                )
                total_stocks += 1

    return total_stocks
