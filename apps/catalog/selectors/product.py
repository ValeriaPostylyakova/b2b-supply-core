from billiard import Value
from django.db.models import Prefetch, Q, Sum
from django.db.models.functions import Coalesce

from apps.catalog.models.stock import Stock


class ProductSelector:
    def __init__(self, initial_queryset, user, action):
        self.queryset = initial_queryset.all()
        self.user = user
        self.action = action

    def get_optimized_queryset(self):
        if self.action == "create":
            return self._for_create()

        if self.action == "list":
            return self._for_list()

        if self.action == "retrieve":
            return self._for_retrieve()

        return self.queryset

    def _for_create(self):
        return self.queryset.select_related("supplier")

    def _for_list(self):
        if self.user.is_supplier and self.user.has_organization:
            queryset = self.queryset.filter(supplier=self.user.organization)
            supplier_filter = Q(stocks__warehouse__supplier=self.user.organization)

            total_quantity = Coalesce(
                Sum("stocks__quantity", filter=supplier_filter), Value(0)
            )
            total_reserved = Coalesce(
                Sum("stocks__reserved_quantity", filter=supplier_filter), Value(0)
            )

            return queryset.annotate(
                available_quantity=total_quantity - total_reserved,
                quantity=total_quantity,
                reserved_quantity=total_reserved,
            )

        all_total_quantity = Coalesce(Sum("stocks__quantity"), Value(0))
        all_total_reserved = Coalesce(Sum("stocks__reserved_quantity"), Value(0))
        return self.queryset.annotate(
            available_quantity=all_total_quantity - all_total_reserved,
        )

    def _for_retrieve(self):
        if self.user.is_supplier and self.user.has_organization:
            queryset = self.queryset.filter(supplier=self.user.organization)
            stock_qs = Stock.objects.filter(warehouse__supplier=self.user.organization)
        else:
            queryset = self.queryset
            stock_qs = Stock.objects.all()

        return queryset.prefetch_related(
            Prefetch("stocks", queryset=stock_qs.select_related("warehouse"))
        )
