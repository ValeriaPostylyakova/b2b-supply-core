from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.catalog.models import Stock
from apps.orders.exceptions import InsufficientStock
from apps.orders.models import FileDocument, Order, OrderItem, Reservation


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order_with_reservations(buyer, supplier, items_data):
        quantities = defaultdict(int)
        for item in items_data:
            quantities[(item["product"].id, item["warehouse"].id)] += item["quantity"]
        sorted_keys = sorted(quantities.keys())

        locked_stocks = {}
        for p_id, w_id in sorted_keys:
            try:
                stock = Stock.objects.select_for_update().get(
                    product_id=p_id, warehouse_id=w_id
                )
                locked_stocks[(p_id, w_id)] = stock
            except Stock.DoesNotExist:
                raise InsufficientStock(
                    product_sku=p_id, available=0, requested=quantities[(p_id, w_id)]
                )

        for (p_id, w_id), requested_qty in quantities.items():
            stock = locked_stocks[(p_id, w_id)]
            available = stock.quantity - stock.reserved_quantity
            if available < requested_qty:
                product_sku = getattr(stock.product, "sku", stock.product_id)
                raise InsufficientStock(
                    product_sku=product_sku,
                    available=available,
                    requested=requested_qty,
                )

        order = Order.objects.create(
            buyer=buyer,
            supplier=supplier,
            status=Order.StatusChoices.RESERVED,
            total_amount=Decimal("0"),
            items_count=len(quantities),
        )

        total_amount = Decimal("0")

        for item in items_data:
            product = item["product"]
            warehouse = item["warehouse"]
            quantity = item["quantity"]
            stock = locked_stocks[(product.id, warehouse.id)]

            line_total = product.price * quantity
            total_amount += line_total

            OrderItem.objects.create(
                order=order,
                product=product,
                warehouse=warehouse,
                quantity=quantity,
                unit_price=product.price,
                line_total=line_total,
            )

            Stock.objects.filter(pk=stock.pk).update(
                reserved_quantity=F("reserved_quantity") + quantity
            )

            Reservation.objects.create(
                order=order,
                stock=stock,
                quantity=quantity,
                status=Reservation.Status.ACTIVE,
                expires_at=timezone.now() + timedelta(days=1),
            )

        order.total_amount = total_amount
        order.save(update_fields=["total_amount"])
        return order

    @staticmethod
    @transaction.atomic
    def cancel_order(order_id):
        order = Order.objects.get(id=order_id)
        reservations = Reservation.objects.filter(order=order)
        stocks = list(
            Stock.objects.select_for_update().filter(reservations__in=reservations)
        )

        for reservation in reservations:
            stock = next(s for s in stocks if s.id == reservation.stock_id)
            stock.reserved_quantity -= reservation.quantity
            stock.save(update_fields=["reserved_quantity"])

            reservation.status = Reservation.Status.RELEASED
            reservation.save(update_fields=["status"])

        order.status = order.StatusChoices.CANCELLED
        order.save(update_fields=["status"])

        return order

    @staticmethod
    def confirm_order(order_id):
        order = Order.objects.get(id=order_id)
        order.status = order.StatusChoices.CONFIRMED
        order.save(update_fields=["status"])
        return order

    @staticmethod
    def get_order_documents(order_id):
        order = Order.objects.get(id=order_id)
        return FileDocument.objects.filter(order=order)
