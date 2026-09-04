import django_filters

from apps.orders.models.order import Order


class OrderFilter(django_filters.rest_framework.FilterSet):
    min_total = django_filters.NumberFilter(
        field_name="total_amount", lookup_expr="gte"
    )
    max_total = django_filters.NumberFilter(
        field_name="total_amount", lookup_expr="lte"
    )

    created_from = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_to = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )

    ordering = django_filters.OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("total_amount", "total_amount"),
        )
    )

    class Meta:
        model = Order
        fields = ["status"]
