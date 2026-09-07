import queue
import threading
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalog.models import Product, Stock, Warehouse
from apps.orders.exceptions import InsufficientStock
from apps.orders.models import Order, OrderItem, Reservation
from apps.orders.services.order import OrderService
from apps.organizations.models import Organization


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def setup_order_data(transactional_db):
    buyer_org = Organization.objects.create(name="Buyer Corp", type="BUYER")
    supplier_org = Organization.objects.create(name="Supplier Corp", type="SUPPLIER")

    buyer_admin = get_user_model().objects.create_user(
        username="buyer_admin_user",
        password="password123",
        organization=buyer_org,
        role="BUYER_ADMIN",
    )

    warehouse = Warehouse.objects.create(
        name="Main WH", supplier=supplier_org, address="Moscow", is_active=True
    )
    product = Product.objects.create(
        name="B2B Product", price=Decimal("100.00"), sku="PROD-1", supplier=supplier_org
    )
    stock = Stock.objects.create(
        product=product, warehouse=warehouse, quantity=10, reserved_quantity=0
    )

    return {
        "user": buyer_admin,
        "supplier": supplier_org,
        "buyer": buyer_org,
        "warehouse": warehouse,
        "product": product,
        "stock": stock,
    }


def test_create_order_success(api_client, setup_order_data):
    data = setup_order_data
    api_client.force_authenticate(user=data["user"])

    payload = {
        "supplier": data["supplier"].external_id,
        "items": [
            {
                "product": data["product"].external_id,
                "warehouse": data["warehouse"].external_id,
                "quantity": 3,
            }
        ],
    }

    url = reverse("orders-list")
    response = api_client.post(url, payload, format="json")

    assert response.status_code == 201
    assert response.data["total_amount"] == "300.00"

    data["stock"].refresh_from_db()
    assert data["stock"].reserved_quantity == 3

    order = Order.objects.get(external_id=response.data["id"])
    assert order.status == "RESERVED"
    assert OrderItem.objects.filter(order=order).count() == 1
    assert Reservation.objects.filter(order=order, status="ACTIVE").count() == 1


def test_create_order_insufficient_stock(api_client, setup_order_data):
    data = setup_order_data
    api_client.force_authenticate(user=data["user"])

    payload = {
        "supplier": data["supplier"].external_id,
        "items": [
            {
                "product": data["product"].external_id,
                "warehouse": data["warehouse"].external_id,
                "quantity": 15,
            }
        ],
    }

    url = reverse("orders-list")
    response = api_client.post(url, payload, format="json")

    assert response.status_code == 409

    data["stock"].refresh_from_db()
    assert data["stock"].reserved_quantity == 0
    assert Order.objects.count() == 0


def test_race_condition_prevented(setup_order_data):
    data = setup_order_data
    items_data = [
        {"product": data["product"], "warehouse": data["warehouse"], "quantity": 6}
    ]

    results_queue = queue.Queue()

    def create_order_in_thread(buyer):
        try:
            OrderService.create_order_with_reservations(
                buyer, data["supplier"], items_data
            )
            results_queue.put("SUCCESS")
        except InsufficientStock:
            results_queue.put("INSUFFICIENT")
        except Exception as e:
            results_queue.put(f"ERROR: {str(e)}")

    buyer_b = Organization.objects.create(name="Buyer Corp B", type="BUYER")

    thread1 = threading.Thread(target=create_order_in_thread, args=(data["buyer"],))
    thread2 = threading.Thread(target=create_order_in_thread, args=(buyer_b,))

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    results = []
    while not results_queue.empty():
        results.append(results_queue.get())

    assert "SUCCESS" in results
    assert "INSUFFICIENT" in results

    data["stock"].refresh_from_db()
    assert data["stock"].reserved_quantity == 6
