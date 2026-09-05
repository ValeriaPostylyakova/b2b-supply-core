import django_filters
from django.db.models import F, Q

from apps.catalog.models.product import Product


class ProductFilter(django_filters.rest_framework.FilterSet):
    search = django_filters.CharFilter(method="filter_search", label="Поиск")

    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    available = django_filters.BooleanFilter(method="filter_available")

    ordering = django_filters.OrderingFilter(
        fields=["price", "created_at", "name"],
        field_labels={
            "price": "Цена",
            "created_at": "Дата создания",
            "name": "Название",
        },
    )

    class Meta:
        model = Product
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(sku__icontains=value)
        ).distinct()

    def filter_available(self, queryset, name, value):
        if value:
            return queryset.filter(stocks__quantity__gt=F("stocks__reserved_quantity"))
        else:
            return queryset.filter(stocks__quantity__lte=F("stocks__reserved_quantity"))
