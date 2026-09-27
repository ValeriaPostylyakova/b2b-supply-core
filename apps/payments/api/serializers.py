from rest_framework import serializers

from apps.orders.models.order import Order


class PaymentInitSerializer(serializers.Serializer):
    order_id = serializers.CharField()

    def validate_order_id(self, value):
        try:
            order = Order.objects.get(external_id=value)

        except Order.DoesNotExist:
            raise serializers.ValidationError("Заказ не найден.")

        if order.status != Order.StatusChoices.RESERVED:
            raise serializers.ValidationError("Данный заказ нельзя оплатить.")
        return value
