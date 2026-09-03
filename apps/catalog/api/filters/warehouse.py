import django_filters
from django.db.models import Q

from apps.catalog.models.warehouse import Warehouse


class WarehouseFilter(django_filters.rest_framework.FilterSet):
    search = django_filters.CharFilter(method="filter_search", label="Поиск")
    ordering = django_filters.OrderingFilter(
        fields=[
            "name",
            "created_at",
        ],
        field_labels={"name": "Название", "created_at": "Дата создания"},
    )

    class Meta:
        model = Warehouse
        fields = ["search", "ordering", "is_active"]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(supplier__name__icontains=value)
        ).distinct()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.request
        if not request or not request.user:
            return

        user = request.user
        if not user.is_supplier:
            self.filters.pop("is_active", None)
