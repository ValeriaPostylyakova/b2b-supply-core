import random
from datetime import timedelta
from datetime import timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.db import transaction
from faker import Faker

from apps.accounts.models import Organization
from apps.catalog.models.product import Product
from apps.catalog.models.stock import Stock
from apps.catalog.models.warehouse import Warehouse
from apps.orders.models import Order, OrderItem, Reservation

User = get_user_model()
fake = Faker(["ru_RU"])


def clean_old_data():
    Reservation.objects.all().delete()
    OrderItem.objects.all().delete()
    Order.objects.all().delete()
    Stock.objects.all().delete()
    User.objects.filter(email__endswith="@example.com").delete()
    Organization.objects.filter(name__endswith=" (Тест)").delete()
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


def seed_orders_and_reservations(orders_count=30):
    buyers = list(Organization.objects.filter(type=Organization.Types.BUYER))
    suppliers = list(Organization.objects.filter(type=Organization.Types.SUPPLIER))

    if not buyers or not suppliers:
        print("Ошибка: Сначала запустите seed_base_data, чтобы создать организации.")
        return

    created_orders_count = 0
    created_reservations_count = 0

    print(f"Начало генерации заказов ({orders_count} шт.)...")

    for _ in range(orders_count):
        buyer = random.choice(buyers)
        supplier = random.choice(suppliers)

        supplier_products = list(
            Product.objects.filter(supplier=supplier, is_active=True)
        )
        supplier_warehouses = list(
            Warehouse.objects.filter(supplier=supplier, is_active=True)
        )

        if not supplier_products or not supplier_warehouses:
            continue

        status = random.choice(Order.StatusChoices.values)

        with transaction.atomic():
            order = Order.objects.create(
                buyer=buyer,
                supplier=supplier,
                status=status,
                created_at=fake.date_time_between(
                    start_date="-30d",
                    end_date="now",
                    tzinfo=datetime_timezone.utc,
                ),
            )

            items_to_create_count = min(random.randint(1, 5), len(supplier_products))
            selected_products = random.sample(supplier_products, items_to_create_count)

            total_amount = 0
            items_count = 0

            for product in selected_products:
                quantity = random.randint(1, 15)
                unit_price = product.price
                line_total = unit_price * quantity
                warehouse = random.choice(supplier_warehouses)

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    warehouse=warehouse,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                )

                total_amount += line_total
                items_count += quantity

                if order.status == Order.StatusChoices.RESERVED:
                    stock = Stock.objects.filter(
                        product=product, warehouse=warehouse
                    ).first()

                    if not stock:
                        stock = Stock.objects.create(
                            product=product,
                            warehouse=warehouse,
                            quantity=random.randint(50, 200),
                            reserved_quantity=0,
                        )

                    expires_at = order.created_at + timedelta(days=3)

                    Reservation.objects.create(
                        order=order,
                        stock=stock,
                        quantity=quantity,
                        status=Reservation.Status.ACTIVE,
                        expires_at=expires_at,
                    )
                    created_reservations_count += 1

            order.items_count = items_count
            order.total_amount = total_amount
            order.save()

            created_orders_count += 1

    print(
        f"Успешно создано: {created_orders_count} заказов и {created_reservations_count} активных резерваций."
    )
    return created_orders_count
