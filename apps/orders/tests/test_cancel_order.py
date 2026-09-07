from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Product, Stock, Warehouse
from apps.orders.models import Order, Reservation


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def setup_cancel_order_data(transactional_db):
    from apps.organizations.models import Organization

    supplier_org = Organization.objects.create(name="Supplier Corp", type="SUPPLIER")
    buyer_org = Organization.objects.create(name="Buyer Corp", type="BUYER")

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
        name="B2B Product", price="100.00", sku="PROD-1", supplier=supplier_org
    )

    stock = Stock.objects.create(
        product=product, warehouse=warehouse, quantity=10, reserved_quantity=5
    )

    order = Order.objects.create(
        buyer=buyer_org,
        supplier=supplier_org,
        status=Order.StatusChoices.RESERVED,
        total_amount="500.00",
    )

    reservation = Reservation.objects.create(
        order=order,
        stock=stock,
        quantity=5,
        status=Reservation.Status.ACTIVE,
        expires_at=timezone.now() + timedelta(days=1),
    )

    return {
        "order": order,
        "stock": stock,
        "reservation": reservation,
        "user": buyer_admin,
    }


@pytest.mark.django_db
def test_cancel_order_success(setup_cancel_order_data, api_client):
    data = setup_cancel_order_data
    api_client.force_authenticate(user=data["user"])

    order = data["order"]

    url = reverse("orders-cancel", kwargs={"external_id": order.external_id})

    response = api_client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["detail"] == "Заказ успешно отменен"

    order.refresh_from_db()
    assert order.status == Order.StatusChoices.CANCELLED

    data["reservation"].refresh_from_db()
    assert data["reservation"].status == Reservation.Status.RELEASED

    data["stock"].refresh_from_db()
    assert data["stock"].reserved_quantity == 0
