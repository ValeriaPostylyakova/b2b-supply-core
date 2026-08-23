from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import F
from rest_framework import permissions, generics

from apps.catalog.models import Product
from apps.catalog.paginations import ProductNumberPagination
from apps.catalog.serializers import (
    ProductListSupplierSerializer,
    ProductListBuyerSerializer,
    ProductFilter,
)

User = get_user_model()


from django.db.models import Sum, Value
from django.db.models.functions import Coalesce

class ProductListGenericAPIView(generics.ListAPIView):
    queryset = Product.objects.select_related('supplier')
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = ProductFilter
    pagination_class = ProductNumberPagination

    def get_serializer_class(self):
        user_role = getattr(self.request.user, "role", "")
        is_supplier_user_role = isinstance(user_role, str) and user_role.startswith(
            "SUPPLIER_"
        )
        if is_supplier_user_role:
            return ProductListSupplierSerializer
        return ProductListBuyerSerializer

    def get_queryset(self):
        queryset = self.queryset.all()

        user = self.request.user
        user_role = getattr(user, "role", "")
        is_supplier_user_role = isinstance(user_role, str) and user_role.startswith(
            "SUPPLIER_"
        )

        if is_supplier_user_role:
            if hasattr(user, "organization") and user.organization:
                queryset = queryset.filter(supplier=user.organization)

            supplier_stock_filter = models.Q(
                stocks__warehouse__supplier=user.organization
            )

            total_quantity = Coalesce(
                Sum("stocks__quantity", filter=supplier_stock_filter), Value(0)
            )
            total_reserved = Coalesce(
                Sum("stocks__reserved_quantity", filter=supplier_stock_filter), Value(0)
            )

            queryset = queryset.annotate(
                available_quantity=total_quantity - total_reserved,
                quantity=total_quantity,
                reserved_quantity=total_reserved,
            )
        else:
            all_total_quantity = Coalesce(Sum("stocks__quantity"), Value(0))
            all_total_reserved = Coalesce(Sum("stocks__reserved_quantity"), Value(0))
            queryset = queryset.annotate(
                available_quantity=all_total_quantity - all_total_reserved,
            )

        return queryset







